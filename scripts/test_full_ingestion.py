import sys
import os
import asyncio
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ingestion import ingestion_service
from app.db.postgres import SessionLocal, init_db
from app.db import models

def create_sample_file(path: str):
    content = """
# Production RAG Architecture
This document describes a multi-agent RAG system.

## Components
1. **Reasoning Engine**: Handles planning and tool selection.
2. **Multi-Agent System**: Specialized agents for different tasks.
3. **Database Layer**: ChromaDB for vectors and SQLite for metadata.

## Ingestion Pipeline
The pipeline uses structure-aware chunking to preserve tables and headings.
It also generates metadata like summaries and keywords for better retrieval.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def test_ingestion():
    init_db()
    db = SessionLocal()
    
    file_path = "sample_doc.md"
    create_sample_file(file_path)
    
    file_hash = str(uuid.uuid4())
    filename = "sample_doc.md"
    
    print(f"Ingesting {filename}...")
    ingestion_service.process_document(file_path, filename, file_hash, db)
    
    # Verify Chunk entries in DB
    doc = db.query(models.Document).filter(models.Document.filename == filename).first()
    if doc:
        chunks = db.query(models.Chunk).filter(models.Chunk.document_id == doc.id).all()
        print(f"Verified: Found {len(chunks)} chunks in Relational DB for {filename}")
        for c in chunks:
            print(f"  - Vector ID: {c.vector_id[:8]}... | Keywords: {c.keywords}")
    else:
        print("Error: Document not found in DB after ingestion.")
    
    db.close()
    if os.path.exists(file_path):
        os.remove(file_path)

if __name__ == "__main__":
    test_ingestion()
