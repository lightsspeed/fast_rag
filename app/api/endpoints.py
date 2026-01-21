from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
import uuid
import time
from pydantic import BaseModel

from app.db.postgres import get_db
from app.db import models
from app.services.chunker import chunker
from app.services.embedder import embedder
from app.services.retriever import retriever
from app.services.generator import generator
from app.services.cache import redis_cache
from app.db.chroma import get_collection
from app.services.ingestion import ingestion_service
from app.core.limiter import limiter

router = APIRouter()

# --- Data Models ---
class ChatRequest(BaseModel):
    query: str
    session_id: str
    user_id: Optional[str] = "anonymous"

class FeedbackRequest(BaseModel):
    query_id: int
    score: int # 1 to 5

class TitleRequest(BaseModel):
    query: str

# --- Endpoints ---

@router.post("/documents/upload")
@limiter.limit("5/minute")
async def upload_document(
    request: Request,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    results = []
    for file in files:
        # Save temp
        temp_dir = "temp_uploads"
        os.makedirs(temp_dir, exist_ok=True)
        file_path = os.path.join(temp_dir, file.filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Hash
        # ... logic to hash file content ...
        file_hash = str(uuid.uuid4()) # Placeholder hash

        # DB Record
        db_doc = models.Document(
            filename=file.filename,
            file_hash=file_hash,
            status="processing"
        )
        db.add(db_doc)
        db.commit()
        db.refresh(db_doc)

        # Background Process
        background_tasks.add_task(ingestion_service.process_document, file_path, file.filename, file_hash, db)
        
        results.append({"filename": file.filename, "status": "processing", "id": db_doc.id})
    
    return {"uploaded": results}

@router.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket, db: Session = Depends(get_db)):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            query = data.get("query")
            session_id = data.get("session_id")
            user_id = data.get("user_id", "anonymous")

            if not query:
                continue

            # 1. Retrieve
            chunks = await retriever.retrieve(query)
            
            # Send Citations
            sources = []
            for chunk in chunks:
                sources.append({
                    "chunk_id": chunk['id'],
                    "content": chunk['text'][:200] + "...",
                    "metadata": chunk['metadata']
                })
            await websocket.send_json({"type": "sources", "sources": sources})

            # 2. Generate (Stream)
            async for token in generator.generate_stream(query, chunks):
                await websocket.send_json({"type": "token", "content": token})
            
            await websocket.send_json({"type": "complete"})
            
            # 3. Log
            # Should be async or background
            log = models.QueryLog(
                user_id=user_id,
                query_text=query,
                retrieved_chunks=len(chunks),
                response_time_ms=0 # TODO: measure time
            )
            # db.add(log) # Need a new session or careful threading with websockets
            # db.commit() 

    except WebSocketDisconnect:
        print("Client disconnected")

@router.post("/feedback")
def submit_feedback(feedback: FeedbackRequest, db: Session = Depends(get_db)):
    # ... update log ...
    return {"status": "ok"}

class TitleRequest(BaseModel):
    query: str

@router.post("/chat/title")
@limiter.limit("20/minute")
async def generate_chat_title(request: TitleRequest, req: Request):
    title = generator.generate_title(request.query)
    return {"title": title}
