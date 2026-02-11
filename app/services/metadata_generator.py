import json
from groq import Groq
from app.core.config import settings
from app.core.rate_limiter import groq_rate_limiter
import logging

logger = logging.getLogger(__name__)

class MetadataGenerator:
    """Generates enriched metadata (summary, keywords, questions) using an LLM."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"

    def generate_metadata(self, chunk_text: str) -> dict:
        """Calls LLM to generate summary, keywords, and questions for a chunk."""
        prompt = f"""
        Analyze the following text chunk from a document and generate:
        1. A concise 1-sentence summary.
        2. A list of 5-8 relevant keywords or entities.
        3. 3 potential questions this chunk can answer accurately.

        Format the output as a JSON object with keys: "summary", "keywords", "questions".

        Text Chunk:
        \"\"\"{chunk_text}\"\"\"
        """

        # CRITICAL OPTIMIZATION: Bypass metadata generation during heavy testing to avoid Rate Limits
        # Remove this return statement for production!
        return {
            "summary": "Metadata generation skipped for optimization.",
            "keywords": ["optimization", "rate-limit-bypass"],
            "questions": []
        }

        try:
            groq_rate_limiter.wait_if_needed()
            completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                response_format={"type": "json_object"},
                timeout=30.0
            )
            
            result = json.loads(completion.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"Failed to generate metadata: {e}")
            return {
                "summary": "",
                "keywords": [],
                "questions": []
            }

metadata_generator = MetadataGenerator()
