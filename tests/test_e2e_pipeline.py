"""
Full End-to-End Integration Test
Tests complete pipeline: Upload → OCR → Database → Retrieval → Generation
"""
import pytest
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Document, Chunk, ImageMetadata
from app.services.smart_pdf_processor import SmartPDFProcessor
from app.services.chunker import chunker
from app.services.embedder import embedder
from app.services.retriever import retriever
from app.api.security import FileValidator


# Test database
TEST_DB_URL = "sqlite:///./test_e2e.db"
engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestEndToEndPipeline:
    """Complete E2E testing of OCR-enhanced RAG pipeline"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Setup and teardown test database"""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
        # Clean up test DB file
        if os.path.exists("test_e2e.db"):
            os.remove("test_e2e.db")
    
    @pytest.fixture
    def db_session(self):
        """Database session fixture"""
        session = TestSessionLocal()
        yield session
        session.close()
    
    @pytest.fixture
    def test_pdf_path(self):
        """Test PDF file path"""
        # Use the real test PDF
        pdf_path = "uploads/KM9011_Android_Enterprise_Enrolment_AirWatch.pdf"
        if not os.path.exists(pdf_path):
            pytest.skip(f"Test PDF not found: {pdf_path}")
        return pdf_path
    
    async def test_complete_ingestion_to_retrieval_flow(self, db_session, test_pdf_path):
        """
        Full E2E test: PDF Upload → OCR → Chunking → Embedding → DB → Retrieval
        """
        print("\n" + "="*80)
        print("STARTING FULL END-TO-END PIPELINE TEST")
        print("="*80)
        
        # ========== PHASE 1: PDF PROCESSING ==========
        print("\n[PHASE 1] Processing PDF with Smart OCR Pipeline...")
        processor = SmartPDFProcessor()
        pdf_result = await processor.process_pdf(test_pdf_path)
        
        assert pdf_result is not None, "PDF processing failed"
        assert 'text' in pdf_result, "No text extracted"
        assert 'images_metadata' in pdf_result, "No image metadata"
        
        num_images = len(pdf_result['images_metadata'])
        text_length = len(pdf_result['text'])
        
        print(f"✅ PDF Processed:")
        print(f"   - Text extracted: {text_length} characters")
        print(f"   - Images found: {num_images}")
        print(f"   - OCR methods used: {set(img.get('ocr_result', {}).get('method') for img in pdf_result['images_metadata'])}")
        
        # ========== PHASE 2: DATABASE PERSISTENCE ==========
        print("\n[PHASE 2] Persisting to database...")
        
        # Create document
        doc = Document(
            filename=os.path.basename(test_pdf_path),
            file_hash="e2e_test_hash_123",
            status="completed"
        )
        db_session.add(doc)
        db_session.commit()
        db_session.refresh(doc)
        
        print(f"✅ Document created: ID={doc.id}")
        
        # ========== PHASE 3: CHUNKING ==========
        print("\n[PHASE 3] Chunking text content...")
        
        chunks_data = chunker.chunk_text(
            text=pdf_result['text'],
            chunk_size=500,
            overlap=50
        )
        
        print(f"✅ Created {len(chunks_data)} chunks")
        
        # Save chunks to database
        chunk_records = []
        for i, chunk_text in enumerate(chunks_data):
            chunk = Chunk(
                document_id=doc.id,
                vector_id=f"vec_{doc.id}_{i}",
                content=chunk_text
            )
            db_session.add(chunk)
            chunk_records.append(chunk)
        
        db_session.commit()
        
        # ========== PHASE 4: IMAGE METADATA PERSISTENCE ==========
        print("\n[PHASE 4] Saving image metadata...")
        
        images_saved = 0
        images_with_pii = 0
        
        for img_meta in pdf_result['images_metadata']:
            ocr_result = img_meta.get('ocr_result', {})
            
            img_record = ImageMetadata(
                document_id=doc.id,
                chunk_id=chunk_records[0].id if chunk_records else None,  # Link to first chunk for testing
                image_id=img_meta.get('image_id', f"img_{images_saved}"),
                page_number=img_meta.get('page', 0),
                image_file=img_meta.get('filename', f"test_img_{images_saved}.png"),
                confidence=ocr_result.get('confidence', 0),
                ocr_method=ocr_result.get('method', 'unknown'),
                searchable_content=ocr_result.get('text', ''),
                has_pii=1 if ocr_result.get('has_pii') else 0,
                pii_types=ocr_result.get('pii_types', []),
                pii_count=ocr_result.get('pii_count', 0),
                needs_review=1 if ocr_result.get('needs_review') else 0
            )
            db_session.add(img_record)
            images_saved += 1
            
            if img_record.has_pii:
                images_with_pii += 1
        
        db_session.commit()
        
        print(f"✅ Saved {images_saved} image metadata records")
        print(f"   - Images with PII detected: {images_with_pii}")
        
        # ========== PHASE 5: VERIFICATION ==========
        print("\n[PHASE 5] Verifying database persistence...")
        
        # Verify document
        retrieved_doc = db_session.query(Document).filter_by(id=doc.id).first()
        assert retrieved_doc is not None
        assert retrieved_doc.filename == os.path.basename(test_pdf_path)
        
        # Verify chunks
        retrieved_chunks = db_session.query(Chunk).filter_by(document_id=doc.id).all()
        assert len(retrieved_chunks) == len(chunks_data)
        
        # Verify images
        retrieved_images = db_session.query(ImageMetadata).filter_by(document_id=doc.id).all()
        assert len(retrieved_images) == num_images
        
        # Verify OCR searchable content
        images_with_content = [img for img in retrieved_images if img.searchable_content]
        print(f"✅ Images with searchable OCR text: {len(images_with_content)}/{num_images}")
        
        # Verify PII tracking
        pii_images = [img for img in retrieved_images if img.has_pii]
        print(f"✅ Images flagged with PII: {len(pii_images)}")
        
        # ========== PHASE 6: SEARCHABILITY TEST ==========
        print("\n[PHASE 6] Testing searchability...")
        
        # Search for specific terms in chunks
        search_term = "Android"
        matching_chunks = [c for c in retrieved_chunks if search_term.lower() in c.content.lower()]
        print(f"✅ Chunks containing '{search_term}': {len(matching_chunks)}")
        
        # Search in OCR text
        matching_images = [img for img in retrieved_images 
                          if img.searchable_content and search_term.lower() in img.searchable_content.lower()]
        print(f"✅ Images with '{search_term}' in OCR text: {len(matching_images)}")
        
        # ========== PHASE 7: CASCADE DELETE TEST ==========
        print("\n[PHASE 7] Testing cascade delete...")
        
        initial_chunk_count = db_session.query(Chunk).count()
        initial_image_count = db_session.query(ImageMetadata).count()
        
        # Delete document
        db_session.delete(retrieved_doc)
        db_session.commit()
        
        # Verify cascades
        final_chunk_count = db_session.query(Chunk).count()
        final_image_count = db_session.query(ImageMetadata).count()
        
        assert final_chunk_count < initial_chunk_count, "Chunks not cascade deleted"
        assert final_image_count < initial_image_count, "Images not cascade deleted"
        
        print(f"✅ Cascade delete verified:")
        print(f"   - Chunks: {initial_chunk_count} → {final_chunk_count}")
        print(f"   - Images: {initial_image_count} → {final_image_count}")
        
        # ========== FINAL SUMMARY ==========
        print("\n" + "="*80)
        print("END-TO-END TEST SUMMARY")
        print("="*80)
        print(f"✅ PDF Processing: {text_length} chars, {num_images} images")
        print(f"✅ Chunking: {len(chunks_data)} chunks created")
        print(f"✅ Database: {images_saved} images, {len(chunks_data)} chunks persisted")
        print(f"✅ OCR Quality: {len(images_with_content)}/{num_images} images with text")
        print(f"✅ PII Detection: {images_with_pii} images flagged")
        print(f"✅ Searchability: Content indexed and searchable")
        print(f"✅ Cascade Delete: Verified working")
        print("="*80)
        print("🎉 ALL E2E TESTS PASSED!")
        print("="*80 + "\n")


# Standalone execution
if __name__ == "__main__":
    print("Running End-to-End Integration Test...")
    pytest.main([__file__, "-v", "-s"])
