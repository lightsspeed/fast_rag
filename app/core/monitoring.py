"""
Monitoring and Observability for OCR Pipeline
Tracks metrics, performance, and quality indicators
"""
from prometheus_client import Counter, Histogram, Gauge, Summary
import time
import logging
from functools import wraps
from typing import Callable

logger = logging.getLogger(__name__)

# Initialize Prometheus metrics

# Counters
ocr_requests_total = Counter(
    'ocr_requests_total',
    'Total OCR processing requests',
    ['method', 'status']
)

pii_detections_total = Counter(
    'pii_detections_total',
    'Total PII detections',
    ['pii_type']
)

file_uploads_total = Counter(
    'file_uploads_total',
    'Total file uploads',
    ['status', 'file_type']
)

# Histograms (for latency distribution)
ocr_duration_seconds = Histogram(
    'ocr_duration_seconds',
    'OCR processing duration in seconds',
    ['engine'],
    buckets=(0.5, 1, 2, 5, 10, 20, 30, 60)
)

ocr_confidence_score = Histogram(
    'ocr_confidence_score',
    'OCR confidence score distribution',
    ['method'],
    buckets=(0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100)
)

pdf_processing_duration = Histogram(
    'pdf_processing_duration_seconds',
    'Full PDF processing duration',
    buckets=(5, 10, 30, 60, 120, 300, 600)
)

# Gauges (for current state)
active_ocr_jobs = Gauge(
    'active_ocr_jobs',
    'Currently active OCR processing jobs'
)

images_processed_today = Counter(
    'images_processed_total',
    'Total images processed since startup'
)

# Summary stats
response_size_bytes = Summary(
    'response_size_bytes',
    'Size of OCR response in bytes'
)


class OCRMonitor:
    """Monitor for OCR operations"""
    
    @staticmethod
    def track_ocr_request(method: str, status: str):
        """Track OCR request"""
        ocr_requests_total.labels(method=method, status=status).inc()
    
    @staticmethod
    def track_ocr_duration(engine: str, duration: float):
        """Track OCR processing duration"""
        ocr_duration_seconds.labels(engine=engine).observe(duration)
    
    @staticmethod
    def track_ocr_confidence(method: str, confidence: float):
        """Track OCR confidence score"""
        ocr_confidence_score.labels(method=method).observe(confidence)
    
    @staticmethod
    def track_pii_detection(pii_types: list):
        """Track PII detections"""
        for pii_type in pii_types:
            pii_detections_total.labels(pii_type=pii_type).inc()
    
    @staticmethod
    def track_file_upload(status: str, file_type: str):
        """Track file upload"""
        file_uploads_total.labels(status=status, file_type=file_type).inc()
    
    @staticmethod
    def track_pdf_processing(duration: float):
        """Track full PDF processing time"""
        pdf_processing_duration.observe(duration)


def monitor_ocr_operation(engine: str):
    """
    Decorator to monitor OCR operations
    
    Usage:
        @monitor_ocr_operation('tesseract')
        def perform_tesseract_ocr(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            active_ocr_jobs.inc()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                
                # Track metrics
                duration = time.time() - start_time
                OCRMonitor.track_ocr_duration(engine, duration)
                OCRMonitor.track_ocr_request(engine, 'success')
                
                # Track confidence if available
                if isinstance(result, dict) and 'confidence' in result:
                    OCRMonitor.track_ocr_confidence(engine, result['confidence'])
                
                # Track PII if detected
                if isinstance(result, dict) and result.get('has_pii'):
                    OCRMonitor.track_pii_detection(result.get('pii_types', []))
                
                images_processed_today.inc()
                
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                OCRMonitor.track_ocr_duration(engine, duration)
                OCRMonitor.track_ocr_request(engine, 'error')
                raise
                
            finally:
                active_ocr_jobs.dec()
        
        return wrapper
    return decorator


def monitor_pdf_processing(func: Callable):
    """
    Decorator to monitor full PDF processing
    
    Usage:
        @monitor_pdf_processing
        async def process_pdf(...):
            ...
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            OCRMonitor.track_pdf_processing(duration)
            
            logger.info(f"PDF processing completed in {duration:.2f}s")
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"PDF processing failed after {duration:.2f}s: {e}")
            raise
    
    return wrapper


# Global monitor instance
ocr_monitor = OCRMonitor()
