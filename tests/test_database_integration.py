"""
Comprehensive database integration and E2E tests for OCR pipeline
"""
import pytest
import os
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.models import Base, Document, Chunk, ImageMetadata
from app.services.smart_pdf_processor import SmartPDFProcessor
from app.api.security import FileValidator
from app.services.pii_detector import pii_detector

# Test database
TEST_DB_URL = "sqlite:///./test_ocr_integration.db"
engine = create_engine(TEST_DB_URL)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestDatabaseIntegration:
    """Test OCR pipeline database persistence"""
    
    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        """Create and drop test database for each test"""
        Base.metadata.create_all(bind=engine)
        yield
        Base.metadata.drop_all(bind=engine)
    
    @pytest.fixture
    def db_session(self):
        """Provide a database session"""
        session = TestSessionLocal()
        yield session
        session.close()
    
    @pytest.fixture
    def test_pdf_path(self):
        """Path to test PDF"""
        return "uploads/KM9011_Android_Enterprise_Enrolment_AirWatch.pdf"
    
    async def test_full_pdf_ingestion_with_images(self, db_session, test_pdf_path):
        """
        Test complete flow: PDF → Images → Database → Persistence
        """
        # 1. Process PDF with smart processor
        processor = SmartPDFProcessor()
        result = await processor.process_pdf(test_pdf_path)
        
        assert result is not None
        assert 'text' in result
        assert 'images_metadata' in result
        assert len(result['images_metadata']) > 0
        
        # 2. Create document record
        doc = Document(
            filename="test_android_kb.pdf",
            file_hash="test_hash_12345",
            status="completed",
            chunk_count=len(result.get('chunks', []))
        )
        db_session.add(doc)
       db_session.commit()
        db_session.refresh(doc)
        
        assert doc.id is not None
        
        # 3. Save image metadata to database
        for img_meta in result['images_metadata']:
            img_record = ImageMetadata(
                document_id=doc.id,
                chunk_id=None,  # Will be linked during chunking
                image_id=img_meta['image_id'],
                page_number=img_meta['page'],
                image_file=img_meta['filename'],
                confidence=img_meta.get('ocr_result', {}).get('confidence', 0),
                ocr_method=img_meta.get('ocr_result', {}).get('method', 'unknown'),
                searchable_content=img_meta.get('ocr_result', {}).get('text', ''),
                screenshot_type=img_meta.get('metadata', {}).get('type', 'general'),
                application=img_meta.get('metadata', {}).get('application', 'Unknown'),
                error_codes=img_meta.get('metadata', {}).get('error_codes', []),
                has_pii=1 if img_meta.get('ocr_result', {}).get('has_pii') else 0,
                pii_types=img_meta.get('ocr_result', {}).get('pii_types', []),
                pii_count=img_meta.get('ocr_result', {}).get('pii_count', 0),
                needs_review=1 if img_meta.get('ocr_result', {}).get('needs_review') else 0,
                redacted_content=img_meta.get('ocr_result', {}).get('redacted_content')
            )
            db_session.add(img_record)
        
        db_session.commit()
        
        # 4. Verify persistence
        retrieved_images = db_session.query(ImageMetadata).filter_by(
            document_id=doc.id
        ).all()
        
        assert len(retrieved_images) == len(result['images_metadata'])
        assert all(img.document_id == doc.id for img in retrieved_images)
        
        # 5. Verify OCR text searchability
        images_with_text = [img for img in retrieved_images if img.searchable_content]
        assert len(images_with_text) > 0
        
        # 6. Verify PII detection ran
        images_with_pii_check = [img for img in retrieved_images if img.has_pii is not None]
        assert len(images_with_pii_check) == len(retrieved_images)
        
        print(f"✅ Full ingestion test passed: {len(retrieved_images)} images persisted")
    
    def test_document_cascade_delete(self, db_session):
        """Test that deleting document cascades to images"""
        # Create document with images
        doc = Document(filename="test.pdf", file_hash="hash123", status="completed")
        db_session.add(doc)
        db_session.commit()
        
        # Add chunks
        chunk = Chunk(
            document_id=doc.id,
            vector_id="vec_123",
            content="Test content"
        )
        db_session.add(chunk)
        db_session.commit()
        
        # Add images linked to chunk
        for i in range(3):
            img = ImageMetadata(
                document_id=doc.id,
                chunk_id=chunk.id,
                image_id=f"img_{i}",
                page_number=1,
                image_file=f"test_{i}.png",
                searchable_content="Test OCR text"
            )
            db_session.add(img)
        db_session.commit()
        
        # Verify images exist
        images = db_session.query(ImageMetadata).filter_by(document_id=doc.id).all()
        assert len(images) == 3
        
        # Delete document
        db_session.delete(doc)
        db_session.commit()
        
        # Verify cascade delete
        images_after = db_session.query(ImageMetadata).filter_by(document_id=doc.id).all()
        chunks_after = db_session.query(Chunk).filter_by(document_id=doc.id).all()
        
        assert len(images_after) == 0
        assert len(chunks_after) == 0
        
        print("✅ Cascade delete test passed")
    
    def test_pii_detection_and_storage(self, db_session):
        """Test PII detection is properly stored"""
        doc = Document(filename="pii_test.pdf", file_hash="pii_hash", status="completed")
        db_session.add(doc)
        db_session.commit()
        
        # Simulate OCR text with PII
        ocr_text_with_pii = "Contact: john.doe@example.com or call 555-123-4567"
        pii_result = pii_detector.redact_pii(ocr_text_with_pii)
        
        img = ImageMetadata(
            document_id=doc.id,
            image_id="pii_img_1",
            page_number=1,
            image_file="pii_screenshot.png",
            searchable_content=ocr_text_with_pii,
            has_pii=1 if pii_result['has_pii'] else 0,
            pii_types=pii_result.get('pii_types', []),
            pii_count=pii_result.get('pii_count', 0),
            redacted_content=pii_result.get('redacted'),
            needs_review=1 if pii_detector.should_flag_for_review(pii_result) else 0
        )
        db_session.add(img)
        db_session.commit()
        
        # Retrieve and verify
        retrieved = db_session.query(ImageMetadata).filter_by(image_id="pii_img_1").first()
        
        assert retrieved.has_pii == 1
        assert retrieved.pii_count > 0
        assert len(retrieved.pii_types) > 0
        assert "EMAIL" in retrieved.pii_types or "PHONE" in retrieved.pii_types
        assert retrieved.redacted_content != retrieved.searchable_content
        
        print(f"✅ PII detection test passed: {retrieved.pii_count} PIIs detected")


class TestFileUploadSecurity:
    """Test file upload security validation"""
    
    async def test_valid_pdf_upload(self):
        """Test valid PDF passes validation"""
        from fastapi import UploadFile
        from io import BytesIO
        
        # Create a minimal valid PDF
        pdf_content = b'%PDF-1.4\n%Test PDF\n%%EOF'
        file = UploadFile(filename="test.pdf", file=BytesIO(pdf_content))
        
        safe_name, file_hash = await FileValidator.validate_upload(file)
        
        assert safe_name == "test.pdf"
        assert len(file_hash) == 64  # SHA256 hex length
        print("✅ Valid PDF upload test passed")
    
    async def test_malicious_filename_rejected(self):
        """Test that path traversal attempts are rejected"""
        from fastapi import UploadFile, HTTPException
        from io import BytesIO
        
        pdf_content = b'%PDF-1.4\n%Test\n%%EOF'
        file = UploadFile(filename="../../../etc/passwd.pdf", file=BytesIO(pdf_content))
        
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_upload(file)
        
        assert "prohibited pattern" in str(exc_info.value.detail).lower()
        print("✅ Malicious filename rejection test passed")
    
    async def test_file_size_limit(self):
        """Test that oversized files are rejected"""
        from fastapi import UploadFile, HTTPException
        from io import BytesIO
        
        # Create file larger than 50MB limit
        large_content = b'A' * (51 * 1024 * 1024)
        file = UploadFile(filename="large.pdf", file=BytesIO(large_content))
        
        with pytest.raises(HTTPException) as exc_info:
            await FileValidator.validate_upload(file)
        
        assert "too large" in str(exc_info.value.detail).lower()
        print("✅ File size limit test passed")


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
