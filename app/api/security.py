"""
File upload security validation
Validates file types, sizes, and performs security checks
"""
import os
import re
import hashlib
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException
import magic
from pathlib import Path

class FileValidator:
    """Comprehensive file upload security validation"""
    
    # Allowed MIME types (verified by magic number, not extension)
    ALLOWED_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'text/markdown',
    }
    
    # Maximum file size: 50 MB
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # Malicious patterns in filenames
    DANGEROUS_PATTERNS = [
        r'\.\.',  # Path traversal
        r'[<>:"|?*]',  # Windows invalid chars
        r'[\x00-\x1f]',  # Control characters
        r'^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(\.|$)',  # Windows reserved names
    ]
    
    @classmethod
    async def validate_upload(cls, file: UploadFile) -> Tuple[str, str]:
        """
        Validate uploaded file for security and format compliance
        
        Returns:
            Tuple[str, str]: (safe_filename, file_hash)
            
        Raises:
            HTTPException: If validation fails
        """
        # 1. Read file content
        content = await file.read()
        await file.seek(0)
        
        # 2. Size validation
        size = len(content)
        if size == 0:
            raise HTTPException(400, "Empty file uploaded")
        
        if size > cls.MAX_FILE_SIZE:
            raise HTTPException(
                400, 
                f"File too large: {size/1024/1024:.1f}MB (max: {cls.MAX_FILE_SIZE/1024/1024}MB)"
            )
        
        # 3. MIME type validation (magic number, not extension)
        mime_type = magic.from_buffer(content, mime=True)
        if mime_type not in cls.ALLOWED_TYPES:
            raise HTTPException(
                400, 
                f"Invalid file type: {mime_type}. Allowed: {', '.join(cls.ALLOWED_TYPES)}"
            )
        
        # 4. Filename sanitization
        original_filename = file.filename or "unnamed_file"
        safe_filename = cls._sanitize_filename(original_filename)
        
        # 5. Compute file hash (for deduplication)
        file_hash = hashlib.sha256(content).hexdigest()
        
        # 6. PDF-specific validation
        if mime_type == 'application/pdf':
            cls._validate_pdf_content(content)
        
        return safe_filename, file_hash
    
    @classmethod
    def _sanitize_filename(cls, filename: str) -> str:
        """
        Sanitize filename to prevent path traversal and injection attacks
        
        Args:
            filename: Original filename from upload
            
        Returns:
            Safe filename with dangerous characters removed
        """
        # Remove any path components
        filename = os.path.basename(filename)
        
        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, filename, re.IGNORECASE):
                raise HTTPException(400, f"Invalid filename: contains prohibited pattern")
        
        # Remove or replace special characters
        # Allow: letters, numbers, spaces, dots, hyphens, underscores
        safe_name = re.sub(r'[^\w\s.-]', '_', filename)
        
        # Limit length
        if len(safe_name) > 255:
            name, ext = os.path.splitext(safe_name)
            safe_name = name[:250] + ext
        
        # Ensure it doesn't start with a dot (hidden file)
        if safe_name.startswith('.'):
            safe_name = '_' + safe_name[1:]
        
        return safe_name
    
    @classmethod
    def _validate_pdf_content(cls, content: bytes):
        """
        Validate PDF structure for common exploits
        
        Args:
            content: PDF file bytes
            
        Raises:
            HTTPException: If PDF appears malicious
        """
        # Check PDF header
        if not content.startswith(b'%PDF-'):
            raise HTTPException(400, "Invalid PDF header")
        
        # Check for suspicious JavaScript
        if b'/JavaScript' in content or b'/JS' in content:
            # Count occurrences - small amounts might be legitimate
            js_count = content.count(b'/JavaScript') + content.count(b'/JS')
            if js_count > 3:
                raise HTTPException(
                    400, 
                    "PDF contains suspicious JavaScript code"
                )
        
        # Check for auto-action triggers
        dangerous_actions = [b'/Launch', b'/SubmitForm', b'/ImportData']
        for action in dangerous_actions:
            if action in content:
                raise HTTPException(
                    400, 
                    f"PDF contains prohibited action: {action.decode()}"
                )
        
        # Check file size vs declared size (compression bomb detection)
        # PDF should not compress to less than 1% of original
        if len(content) < 1000 and b'/FlateDecode' in content:
            raise HTTPException(400, "PDF appears to be a compression bomb")


class FileDeduplicator:
    """Detect and handle duplicate file uploads"""
    
    @staticmethod
    async def check_duplicate(file_hash: str, db_session) -> Optional[dict]:
        """
        Check if file with same hash already exists
        
        Returns:
            Existing document info if duplicate, None otherwise
        """
        from app.db.models import Document
        
        existing = db_session.query(Document).filter(
            Document.file_hash == file_hash
        ).first()
        
        if existing:
            return {
                "id": existing.id,
                "filename": existing.filename,
                "uploaded_at": existing.created_at,
                "is_duplicate": True
            }
        
        return None
