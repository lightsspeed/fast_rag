import json
from groq import Groq
from app.core.config import settings
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class QueryClassifier:
    """
    Lightweight classification layer to determine query intent and tool requirements
    BEFORE the heavy Planner runs.
    """
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        # Use the fast model for low-latency classification
        self.model = settings.GROQ_FAST_MODEL 

    def classify_query(self, query: str) -> Dict[str, Any]:
        """
        Classifies the query to determine if it requires computation or external execution.
        Returns a dictionary with classification flags.
        """
        system_prompt = """You are a highly efficient query classifier. 
Your ONLY job is to analyze the USER QUERY and output a JSON object classifying its intent.

Classify into one of these 'type' categories:
- "conceptual": Questions about concepts, definitions, or high-level explanations. (e.g., "What is a Pod?")
- "procedural": How-to guides, steps, or configuration instructions. (e.g., "How do I install Helm?")
- "debugging": Troubleshooting specific errors or issues. (e.g., "My pod is crashing with BackOff.")
- "computational": Requests involving math, data analysis, specific code execution, or logic puzzles. (e.g., "Calculate 5*5", "Run this python script")
- "out_of_domain": completely unrelated to tech/devops.

Determine flags:
- "requires_computation": true IF AND ONLY IF the query explicitly asks for math, data processing, or code execution. simple info retrieval is FALSE.
- "requires_external_execution": true if it needs to run a command or script to get an answer (rare for chat).

Output format (JSON ONLY):
{
  "type": "category",
  "requires_computation": true/false,
  "requires_external_execution": true/false
}
"""
        
        try:
            completion = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                model=self.model,
                response_format={"type": "json_object"},
                temperature=0.0, # Deterministic
                max_tokens=150
            )
            
            result = json.loads(completion.choices[0].message.content)
            logger.info(f"Query Classification: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Query classifications failed: {e}")
            # Fail safe: Assume NO heavy tools required to be safe, or allow all?
            # User requested "Hard Gating", so defaulting to FALSE for computation is safer 
            # to prevent hallucinated code execution, but might break valid complex queries if classifier fails.
            # Let's default to allowing everything IF classification fails, to avoid breaking the system entirely.
            # BUT user said "Hard Gating". 
            # Let's return a neutral default.
            return {
                "type": "general",
                "requires_computation": False, 
                "requires_external_execution": False
            }

query_classifier = QueryClassifier()
