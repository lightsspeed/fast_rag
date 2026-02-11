import time
import logging
from functools import wraps
from typing import Callable, Any

logger = logging.getLogger(__name__)

class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, calls_per_minute: int = 30):
        self.calls_per_minute = calls_per_minute
        self.min_interval = 60.0 / calls_per_minute
        self.last_call_time = 0
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        current_time = time.time()
        time_since_last_call = current_time - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator to add exponential backoff retry logic to functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_msg = str(e).lower()
                    
                    # Check if it's a rate limit error
                    if 'rate' in error_msg or '429' in error_msg or 'too many requests' in error_msg:
                        if attempt < max_retries - 1:
                            # Exponential backoff: 2^attempt * base_delay
                            delay = (2 ** attempt) * base_delay
                            logger.warning(f"Rate limit hit. Retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                            time.sleep(delay)
                            continue
                    
                    # For other errors, raise immediately
                    raise
            
            # If all retries failed, raise the last exception
            raise last_exception
        
        return wrapper
    return decorator

# Global rate limiter instance (30 requests per minute for Groq free tier)
groq_rate_limiter = RateLimiter(calls_per_minute=25)

class TokenBudgetManager:
    """
    Manages token usage and circuit breaking for LLM models.
    Prevents hitting 429s by tracking 'reset' times from previous errors.
    """
    def __init__(self):
        # Maps model_name -> timestamp (when it becomes available again)
        self._locks: dict[str, float] = {}
        
    def can_use(self, model: str) -> bool:
        """Check if a model is available (not locked)."""
        if model not in self._locks:
            return True
            
        reset_time = self._locks[model]
        if time.time() > reset_time:
            # Lock expired
            del self._locks[model]
            return True
        
        return False

    def report_429(self, model: str, error_msg: str):
        """
        Parses 429 error message to extract wait time and lock the model.
        Example: "Please try again in 3m34.272s"
        """
        import re
        
        # Default wait if parsing fails
        wait_seconds = 60 
        
        # Regex to find "Please try again in X"
        match = re.search(r"try again in (\d+m)?(\d+(\.\d+)?s)?", str(error_msg))
        if match:
            minutes_str = match.group(1)
            seconds_str = match.group(2)
            
            total_seconds = 0
            if minutes_str:
                total_seconds += float(minutes_str.replace('m', '')) * 60
            if seconds_str:
                total_seconds += float(seconds_str.replace('s', ''))
                
            if total_seconds > 0:
                wait_seconds = total_seconds + 5 # Add buffer

        lock_until = time.time() + wait_seconds
        self._locks[model] = lock_until
        logger.warning(f"📉 CIRCUIT BREAKER: Locking model '{model}' for {wait_seconds:.2f}s due to Rate Limit.")
    
    def get_lock_duration(self, model: str) -> float:
        if model not in self._locks:
            return 0.0
        return max(0.0, self._locks[model] - time.time())

token_budget = TokenBudgetManager()
