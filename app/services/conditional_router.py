from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ConditionalRouter:
    """Evaluates execution results and decides the next module (Synthesis, Agents, or Human)."""
    
    def route(self, plan: Dict[str, Any], results: List[Dict[str, Any]]) -> str:
        """Determines where the flow goes next."""
        
        # Logic based on confidence, completeness, or explicit plan requirements
        # Simple implementation for now:
        
        has_results = any(res.get("output") for res in results if res.get("tool") != "summarizer")
        
        if not has_results:
            logger.info("No sufficient results found. Routing to Multi-Agent System for deeper research.")
            return "multi_agent_system"
            
        # If confidence is low or query is sensitive (could check keywords)
        # return "human_validation"
        
        logger.info("Results found. Routing to Synthesis/Generator.")
        return "generator"

conditional_router = ConditionalRouter()
