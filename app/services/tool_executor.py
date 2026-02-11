from typing import List, Dict, Any
from app.services.web_search import web_search
import logging

logger = logging.getLogger(__name__)

class ToolExecutor:
    """Orchestrates the execution of specific tools requested by the Planner."""
    
    async def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = step.get("tool")
        tool_input = step.get("input")
        step_id = step.get("step_id")
        
        
        if not isinstance(step, dict):
             logger.error("Step must be a dictionary.")
             return {"step_id": step_id, "tool": tool_name, "output": "Error: Step is not a dict"}

        logger.info(f"Executing Step {step_id}: {tool_name} with input: {tool_input}")
        
        # 1. Structural Validation
        if not tool_name or tool_input is None:
             logger.error(f"Malformed step: tool={tool_name}, input={tool_input}")
             return {"step_id": step_id, "tool": tool_name, "output": "Error: Malformed step (missing name or input)"}

        # 2. Type Sanitization & Validation
        if isinstance(tool_input, dict):
            # Try common keys
            tool_input = tool_input.get('query') or tool_input.get('input') or tool_input.get('code') or str(tool_input)
            logger.warning(f"Sanitized dict input to string: {tool_input}")
        elif isinstance(tool_input, list):
            # Join list elements
            tool_input = " ".join(str(x) for x in tool_input)
            logger.warning(f"Sanitized list input to string: {tool_input}")
        
        # Hard check: must be string by now
        if not isinstance(tool_input, str):
             logger.error(f"Tool input is not a string after sanitization: {type(tool_input)}")
             return {"step_id": step_id, "tool": tool_name, "output": f"Error: Input type mismatch ({type(tool_input)})"}

        result = {"step_id": step_id, "tool": tool_name, "output": None}
        
        try:
            if tool_name == "hybrid_retriever":
                from app.services.retriever import get_retriever
                result["output"] = await get_retriever().retrieve(tool_input)
            elif tool_name == "web_search":
                result["output"] = await web_search.search(tool_input)
            elif tool_name == "summarizer":
                # Basic summarization logic (can be expanded)
                result["output"] = f"Summary of: {tool_input[:100]}..." 
            elif tool_name == "code_interpreter":
                result["output"] = "Code execution result placeholder"
            else:
                logger.warning(f"Unknown tool: {tool_name}")
                result["output"] = "Error: Unknown tool"
                
            return result
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {"step_id": step_id, "tool": tool_name, "output": f"Error: {str(e)}"}

tool_executor = ToolExecutor()
