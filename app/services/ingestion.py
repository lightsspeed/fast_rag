import os
import uuid
import time
from sqlalchemy.orm import Session
from app.db import models
from app.services.chunker import chunker
from app.services.embedder import embedder
from app.db.chroma import get_collection

import logging

logger = logging.getLogger(__name__)

class IngestionService:
    def process_all_in_dir(self, directory: str, db: Session):
        """Scans directory and processes all files."""
        if not os.path.exists(directory):
            logger.warning(f"Directory {directory} does not exist. Skipping startup scan.")
            return

        files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
        
        if not files:
            logger.info(f"Folder {directory} is empty.")
            return

        logger.info(f"Found {len(files)} files in {directory}. Starting batch processing...")

        for filename in files:
            file_path = os.path.join(directory, filename)
            # Create a dummy hash for local files since we don't have request context
            file_hash = str(uuid.uuid5(uuid.NAMESPACE_DNS, filename)) 
            
            # Check if likely already processed (basic check)
            existing = db.query(models.Document).filter(models.Document.filename == filename).first()
            if existing and existing.status == "completed":
               logger.info(f"Skipping {filename} (already processed)")
               continue

            # Create Record
            try:
                # Check for existing
                existing = db.query(models.Document).filter(models.Document.filename == filename).first()
                if not existing:
                    db_doc = models.Document(
                        filename=filename,
                        file_hash=file_hash,
                        status="processing"
                    )
                    db.add(db_doc)
                    db.commit()
                
                self.process_document(file_path, filename, file_hash, db)
            except Exception as e:
                logger.error(f"Failed to initiate processing for {filename}: {e}")

    def process_document(self, file_path: str, filename: str, file_hash: str, db: Session):
        start_time = time.time()
        logger.info(f"START PROCESSING: {filename}")
        content = ""
        ext = os.path.splitext(filename)[1].lower()
        
        try:
            if ext == ".pdf":
                try:
                    from app.services.smart_pdf_processor import smart_pdf_processor
                    # Use async processing
                    import asyncio
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                    content = loop.run_until_complete(smart_pdf_processor.process_pdf(file_path))
                    
                except Exception as e:
                    logger.error(f"Smart PDF processing error: {e}")
                    # Fallback to basic if smart processor completely fails
                    import pypdf
                    reader = pypdf.PdfReader(file_path)
                    for page in reader.pages:
                        extracted = page.extract_text()
                        if extracted:
                            content += extracted + "\n"
            else:
                # Text/Markdown
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

            if not content.strip():
                logger.warning(f"No content extracted from {filename}")
                self._mark_failed(db, file_hash)
                return

            # 2. Chunk
            logger.info(f"Chunking {filename}...")
            metadata = {
                'source': filename, 
                'filename': filename,
                'upload_time': time.time(), 
                'file_hash': file_hash
            }
            chunks = chunker.chunk_text(content, metadata)
            chunk_count = len(chunks)
            logger.info(f"Generated {chunk_count} chunks for {filename}")

            if not chunks:
                logger.warning("No chunks generated.")
                self._mark_failed(db, file_hash)
                return

            # 3. Embed
            logger.info(f"Embedding {chunk_count} chunks...")
            texts = [chunk['text'] for chunk in chunks]
            embeddings = embedder.embed_batch(texts) 

            # 4. Store in Chroma
            logger.info(f"Storing {chunk_count} vectors in Database...")
            collection = get_collection()
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [chunk['metadata'] for chunk in chunks]
            
            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids
            )

            # 5. Update DB status
            doc = db.query(models.Document).filter(models.Document.file_hash == file_hash).first()
            if doc:
                doc.status = "completed"
                doc.chunk_count = len(chunks)
                db.commit()
            
            elapsed_time = time.time() - start_time
            logger.info(
                f"\n--- Processing Summary ---\n"
                f"File: {filename}\n"
                f"Status: Processed & Stored inside SQLite (ragdb.db)\n"
                f"Chunks Generated: {chunk_count}\n"
                f"Time: ~{elapsed_time:.2f} seconds\n"
                f"--------------------------"
            )
                
        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            self._mark_failed(db, file_hash)

    def _mark_failed(self, db, file_hash):
        doc = db.query(models.Document).filter(models.Document.file_hash == file_hash).first()
        if doc:
            doc.status = "failed"
            db.commit()

ingestion_service = IngestionService()
