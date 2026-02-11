import json
from groq import Groq
from app.core.config import settings
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ResponseEvaluator:
    """Acts as an LLM Judge to evaluate the quality and safety of the generated responses."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    async def evaluate(self, query: str, response: str, context: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluates the response based on faithfulness, relevance, and helpfulness."""
        
        system_prompt = """
        You are a highly critical LLM Judge for a production RAG system.
        Evaluate the provided response based on the query and context.
        
        Metrics:
        1. Faithfulness (0.0-1.0): Does the response adhere exactly to the context? If the answer assumes external tools/commands not mentioned or inappropriate, penalize.
        2. Relevance (0.0-1.0): Does the response directly address the user's constraints?
        3. Helpfulness (0.0-1.0): Is the answer actually correct for the specific scenario?
        4. Context Adherence (0.0-1.0): Does the answer use the provided context? Score 0.0 if the answer is generic knowledge not found in the chunks.
        
        Strictness Level: HIGH
        - If the query implies specific constraints (e.g. "no shell", "read-only", "offline") and the answer ignores them, score Helpfulness < 0.5.
        - If the answer contains specific details (like specific command flags) that are NOT in the context, score Faithfulness < 0.7 (Hallucination check).
        
        Output Format (JSON):
        {
            "scores": {
                "faithfulness": 0.0,
                "relevance": 0.0,
                "helpfulness": 0.0,
                "context_adherence": 0.0
            },
            "overall_grade": "Pass" | "Fail",  # Fail if ANY score < 0.7
            "reasoning": "Explanation of scores."
        }
        """

        for attempt in range(3):
            try:
                completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"Query: {query}\nContext: {context}\nResponse: {response}"}
                    ],
                    model=self.model,
                    response_format={"type": "json_object"}
                )
                
                content = completion.choices[0].message.content
                if not content:
                    raise ValueError("Empty response from Judge")
                    
                evaluation = json.loads(content)
                logger.info(f"Response Evaluation: {evaluation.get('overall_grade', 'Unknown')} ({evaluation.get('scores', {})})")
                return evaluation
                
            except Exception as e:
                logger.warning(f"Evaluation attempt {attempt+1} failed: {e}")
                if attempt == 2:
                    logger.error("Judge system failed all retries. Defaulting to FAIL.")
                    return {
                        "overall_grade": "Fail", 
                        "reasoning": f"Judge System Failure: {str(e)}. Defaulting to safety.",
                        "scores": {"faithfulness": 0.0, "relevance": 0.0, "helpfulness": 0.0, "context_adherence": 0.0}
                    }

response_evaluator = ResponseEvaluator()
