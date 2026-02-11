
import sys
import os
import hashlib
import logging

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ingestion import ingestion_service
from app.db.postgres import SessionLocal
from app.db.models import Document

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def calculate_file_hash(file_path):
    import hashlib
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def ingest_all():
    upload_dir = "uploads"
    if not os.path.exists(upload_dir):
        logger.error(f"Upload directory '{upload_dir}' does not exist.")
        return

    files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
    logger.info(f"Found {len(files)} files in {upload_dir}")

    db = SessionLocal()
    try:
        for filename in files:
            file_path = os.path.join(upload_dir, filename)
            file_hash = calculate_file_hash(file_path)
            
            logger.info(f"Checking {filename} ({file_hash})...")
            
            existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
            
            should_process = False
            if not existing_doc:
                logger.info(f"New document detected: {filename}")
                new_doc = Document(filename=filename, file_hash=file_hash, status="processing")
                db.add(new_doc)
                db.commit()
                should_process = True
            elif existing_doc.status != "completed":
                logger.warning(f"Document {filename} in state '{existing_doc.status}'. Re-processing.")
                existing_doc.status = "processing"
                db.commit()
                should_process = True
            else:
                logger.info(f"Document {filename} already completed. Skipping.")
                
            if should_process:
                try:
                    ingestion_service.process_document(file_path, filename, file_hash, db)
                except Exception as e:
                    logger.error(f"Failed to process {filename}: {e}")
                    
    except KeyboardInterrupt:
        logger.warning("Ingestion stopped by user.")
    finally:
        db.close()
        logger.info("Bulk ingestion check complete.")

if __name__ == "__main__":
    ingest_all()
