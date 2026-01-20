from sqlalchemy import Column, Integer, String, DateTime, JSON, TIMESTAMP, text, func
from sqlalchemy.ext.declarative import declarative_base
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
    # 'metadata' is reserved in some contexts, safely naming column but mapping to 'metadata' might be needed.
    # We use 'doc_metadata' mapped to the 'metadata' column name.
    doc_metadata = Column("metadata", JSON, default={})

class QueryLog(Base):
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(100))
    query_text = Column(String) # Text is better but String is ok
    retrieved_chunks = Column(Integer)
    response_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    feedback_score = Column(Integer, nullable=True)
