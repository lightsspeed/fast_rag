from sqlalchemy import Column, Integer, String, DateTime, JSON, TIMESTAMP, text, func, ForeignKey, Text, Float
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
    images = relationship("ImageMetadata", back_populates="chunk", cascade="all, delete-orphan")

class ImageMetadata(Base):
    __tablename__ = "image_metadata"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("chunks.id"), nullable=True)
    document_id = Column(Integer, nullable=True)
    page_number = Column(Integer, nullable=False)
    image_file = Column(String(500), nullable=False)
    image_id = Column(String(50), unique=True, index=True)
    
    # OCR & Quality Metrics
    ocr_result = Column(JSON, default={})
    confidence = Column(Float, default=0.0)
    ocr_method = Column(String(50))
    resolution = Column(String(50))
    
    # Content & Context
    searchable_content = Column(Text)
    screenshot_type = Column(String(100))
    application = Column(String(100))
    error_codes = Column(JSON, default=[])
    caption = Column(Text, nullable=True)
    context_summary = Column(Text, nullable=True)
    
    # PII Detection Fields
    has_pii = Column(Integer, default=0)  # 0=no, 1=yes
    pii_types = Column(JSON, default=[])  # ["EMAIL", "PHONE"]
    pii_count = Column(Integer, default=0)
    needs_review = Column(Integer, default=0)  # 0=no, 1=yes
    redacted_content = Column(Text, nullable=True)  # Redacted OCR text for logs
    surrounding_text = Column(Text)
    
    chunk = relationship("Chunk", back_populates="images")

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100))
    query_text = Column(String) 
    retrieved_chunks = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    feedback_score = Column(Integer, nullable=True)
