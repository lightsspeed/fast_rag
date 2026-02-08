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
from app.services.vision import vision_service
from app.core.limiter import limiter
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
            session_id = data.get("session_id", "default")
            user_id = data.get("user_id", "anonymous")
            images = data.get("images", [])

            # Load session context to prevent "context bleeding"
            session_context = redis_cache.get_session(session_id, user_id) or {}
            last_visual_context = session_context.get("last_visual_context", "")

            if images:
                logger.info(f"Switching to MULTIMODAL flow for {len(images)} images")
                try:
                    # 1. Extract visual keywords for better RAG retrieval
                    visual_keywords = await vision_service.get_visual_keywords(images[0])
                    augmented_query = query
                    if visual_keywords:
                         augmented_query = f"{query} (context: {visual_keywords})"
                    
                    # Store this context for the next turn
                    session_context["last_visual_context"] = visual_keywords
                    redis_cache.update_session(session_id, user_id, session_context)
                    
                    logger.info(f"Augmented query for RAG: {augmented_query}")

                    # 2. Retrieve RAG context using augmented query
                    chunks = await retriever.retrieve(augmented_query)
                    
                    # Send Citations
                    sources = []
                    for chunk in chunks:
                        metadata = chunk.get('metadata', {})
                        source_name = metadata.get('source', metadata.get('filename', 'Unknown'))
                        sources.append({
                            "id": chunk['id'],
                            "documentName": source_name,
                            "excerpt": chunk['text'][:300],
                            "confidence": chunk.get('score', 0.0),
                            "pageNumber": metadata.get('page'),
                            "title": metadata.get('title'),
                            "isWeb": metadata.get('is_web', False)
                        })
                    await websocket.send_json({"type": "sources", "sources": sources})

                    # 3. Generate multimodal response
                    async for token in vision_service.generate_multimodal_stream(query, images, chunks):
                        await websocket.send_json({"type": "token", "content": token})
                    
                    await websocket.send_json({"type": "complete"})
                    continue 

                except Exception as e:
                    logger.error(f"Multimodal flow failed for session {session_id}: {str(e)}", exc_info=True)
                    await websocket.send_json({"type": "error", "message": "Failed to process image and query together."})
                    continue

            if not query:
                continue

            # --- Standard Text-Only Flow (Groq/Llama) ---
            # 1. Augment Query with previous visual context if it exists
            retrieval_query = query
            if last_visual_context:
                retrieval_query = f"{query} (previously identified: {last_visual_context})"
                logger.info(f"Augmenting text-only query with visual memory: {retrieval_query}")

            # 2. Retrieve
            chunks = await retriever.retrieve(retrieval_query)
            
            # Send Citations
            sources = []
            for chunk in chunks:
                metadata = chunk.get('metadata', {})
                source_name = metadata.get('source', metadata.get('filename', 'Unknown'))
                sources.append({
                    "id": chunk['id'],
                    "documentName": source_name,
                    "excerpt": chunk['text'][:300],
                    "confidence": chunk.get('score', 0.0),
                    "pageNumber": metadata.get('page'),
                    "title": metadata.get('title'),
                    "isWeb": metadata.get('is_web', False)
                })
            await websocket.send_json({"type": "sources", "sources": sources})

            # 3. Generate (Stream)
            async for token in generator.generate_stream(query, chunks):
                await websocket.send_json({"type": "token", "content": token})
            
            await websocket.send_json({"type": "complete"})
            
            # 4. Log
            log = models.QueryLog(
                user_id=user_id,
                query_text=query,
                retrieved_chunks=len(chunks),
                response_time_ms=0 
            )
            # db.add(log)
            # db.commit() 

    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error in session {session_id}: {str(e)}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass

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

# --- Vision Analysis ---

class VisionAnalysisRequest(BaseModel):
    image_data: str  # Base64 data URL
    prompt: Optional[str] = None  # Optional question about the image

class VisionAnalysisResponse(BaseModel):
    analysis: str
    model: str
    tokens_used: Optional[int] = None

@router.post("/vision/analyze", response_model=VisionAnalysisResponse)
@limiter.limit("5/minute")
async def analyze_image(
    body: VisionAnalysisRequest,
    request: Request
):
    """
    Analyze an image using Claude's vision API.
    
    Args:
        body: VisionAnalysisRequest with image_data (base64 data URL) and optional prompt
        request: FastAPI Request object (required for rate limiting)
        
    Returns:
        VisionAnalysisResponse with analysis text, model name, and token usage
        
    Raises:
        HTTPException: For validation errors or API failures
    """
    from app.services.vision import vision_service
    
    try:
        # Use unified method that selects provider based on config
        result = await vision_service.analyze_image(
            image_data=body.image_data,
            prompt=body.prompt
        )
        return VisionAnalysisResponse(**result)
    except ValueError as e:
        # Configuration or validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # API or other errors
        logger.error(f"Vision analysis endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Vision analysis failed: {str(e)}")
