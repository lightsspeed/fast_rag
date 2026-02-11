import time
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class TelemetryService:
    """Tracks latency and estimates costs for the RAG pipeline."""
    
    def __init__(self):
        # Estimated cost per 1M tokens for llama-3.3-70b (example rates)
        self.input_rate = 0.59  # $ / 1M tokens
        self.output_rate = 0.79 # $ / 1M tokens

    def start_timer(self) -> float:
        return time.perf_counter()

    def stop_timer(self, start_time: float) -> float:
        return (time.perf_counter() - start_time) * 1000 # Return ms

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculates estimated USD cost for the Groq call."""
        input_cost = (input_tokens / 1_000_000) * self.input_rate
        output_cost = (output_tokens / 1_000_000) * self.output_rate
        return input_cost + output_cost

telemetry = TelemetryService()
