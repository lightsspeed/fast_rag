from sqlalchemy import Column, Integer, String, DateTime, JSON, TIMESTAMP, text, func, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), unique=True, index=True)
    upload_date = Column(DateTime, default=datetime.utcnow)
    chunk_count = Column(Integer, default=0)
    status = Column(String(50))  # e.g., 'processing', 'completed', 'failed'
    doc_metadata = Column("metadata", JSON, default={})
    
    # Relationship to chunks
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    vector_id = Column(String(64), unique=True, index=True) # ID in ChromaDB
    content = Column(Text, nullable=False)
    summary = Column(Text)
    keywords = Column(JSON, default=[])
    questions = Column(JSON, default=[])
    
    document = relationship("Document", back_populates="chunks")

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100))
    query_text = Column(String) 
    retrieved_chunks = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    feedback_score = Column(Integer, nullable=True)
