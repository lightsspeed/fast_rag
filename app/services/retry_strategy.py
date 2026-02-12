"""
Retry Strategy with Circuit Breaker for OCR Services
Handles transient failures and prevents cascading failures
"""
from tenacity import (
    retry, 
    stop_after_attempt, 
    wait_exponential, 
    retry_if_exception_type,
    before_sleep_log
)
from circuitbreaker import circuit
import logging

logger = logging.getLogger(__name__)


class OCRRetryStrategy:
    """Retry configuration for OCR operations"""
    
    # Retry for transient errors
    PADDLE_RETRY = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, RuntimeError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True
    )
    
    # Circuit breaker to prevent repeated calls to failing service
    @staticmethod
    @circuit(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)
    def paddle_ocr_call_with_circuit_breaker(paddle_instance, img_cv):
        """
        PaddleOCR call with circuit breaker
        
        If PaddleOCR fails 5 times, circuit opens for 60 seconds
        preventing cascading failures
        """
        if paddle_instance is None:
            raise RuntimeError("PaddleOCR instance not available")
        
        result = paddle_instance.ocr(img_cv)
        
        if not result or not result[0]:
            raise RuntimeError("PaddleOCR returned empty result")
        
        return result


def with_paddle_retry(func):
    """Decorator to add retry logic to PaddleOCR calls"""
    return OCRRetryStrategy.PADDLE_RETRY(func)
