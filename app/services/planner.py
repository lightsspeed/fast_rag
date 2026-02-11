from pydantic import BaseModel, Field, ValidationError
from enum import Enum
from groq import Groq
from app.core.config import settings
from app.core.rate_limiter import groq_rate_limiter, with_retry
from typing import List, Dict, Any, Optional
import logging
import json
import re

logger = logging.getLogger(__name__)

class PlannerAction(str, Enum):
    EXECUTE = "execute"
    REFUSE = "refuse"
    REGISTRY_VIOLATION = "registry_violation"

class PlanStep(BaseModel):
    step_id: int = Field(..., description="Unique sequential ID for the step.")
    tool: str = Field(..., description="EXACT name of the tool from available tools.")
    input: str = Field(..., description="Search query or input parameter for the tool.")
    reason: str = Field(..., description="Justification for why this tool is used.")

class ExecutionPlan(BaseModel):
    query_analysis: str = Field(..., description="Technical breakdown of the user intent.")
    action: PlannerAction = Field(default=PlannerAction.EXECUTE, description="The intended system action.")
    steps: List[PlanStep] = Field(default_factory=list, description="Sequence of tool calls to execute.")
    final_instruction: str = Field(..., description="Guidance on how to synthesize the final response.")

class Planner:
    """The brain of the system. Analyzes the query and creates a multi-step execution plan."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_PLANNING_MODEL

    async def create_plan(self, query: str, available_tools_str: str, critique: Optional[str] = None) -> Dict[str, Any]:
        """Decomposes a query into steps using the provided available tools."""
        from app.core.rate_limiter import token_budget
        
        # 1. Structured Tool Registry Injection
        # Convert the existing string list (from ReasoningEngine) into structured JSON objects
        # Format: '1. "tool_name": description'
        tools = []
        for line in available_tools_str.split("\n"):
            match = re.search(r'"([^"]+)":\s*(.*)', line)
            if match:
                tools.append({"name": match.group(1), "description": match.group(2)})
        
        available_tools_json = json.dumps(tools, indent=2)
        allowed_tool_names = [t["name"] for t in tools]

        # 2. Loop-based model selection (Circuit Breaker)
        models_to_try = [settings.GROQ_PLANNING_MODEL, settings.GROQ_FAST_MODEL]
        
        feedback_clause = ""
        if critique:
            feedback_clause = f"\nCRITICAL FEEDBACK ON PREVIOUS PLAN: {critique}\nYour previous plan resulted in a poor evaluation or registry error. Adjust your strategy to address this feedback."

        for model_tier in models_to_try:
            if not token_budget.can_use(model_tier):
                logger.warning(f"⚠️ Budget Constraint: {model_tier} is locked. Trying next tier.")
                continue

            system_prompt = f"""
            🧱 STRICT PLANNER SYSTEM PROMPT (Pydantic-Aligned)
            You are a precision execution planner. Your role is to decompose user queries into atomic steps using ONLY the tool names provided in the registry.

            AVAILABLE TOOLS (STRICT REGISTRY):
            {available_tools_json}

            STRICT REGISTRY ENFORCEMENT:
            1. **VERIFICATION**: Before producing your final JSON, extract every "tool" value and compare it against the names in the AVAILABLE TOOLS list.
            2. **NO HALLUCINATIONS**: If a tool is not in the registry, you MUST NOT use it.
            3. **VIOLATION HANDLING**: If you cannot answer without an unavailable tool, set "action" to "registry_violation" and leave "steps" empty.
            
            CORE DIRECTIVES:
            - **Action Choice**: Use "execute" for valid plans, "refuse" if context is missing or out of scope, or "registry_violation" for tool mismatch.
            - **No Simulation**: Do not invent results.
            - **Efficiency**: Use the minimum steps required.

            {feedback_clause}

            OUTPUT FORMAT (Strict JSON):
            You must return a JSON object matching this schema:
            {{
              "query_analysis": "string",
              "action": "execute" | "refuse" | "registry_violation",
              "steps": [
                 {{
                   "step_id": integer,
                   "tool": "EXACT_NAME",
                   "input": "string",
                   "reason": "string"
                 }}
              ],
              "final_instruction": "string"
            }}
            """

            try:
                groq_rate_limiter.wait_if_needed()
                completion = self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": f"User Query: {query}"}
                    ],
                    model=model_tier,
                    response_format={"type": "json_object"},
                    timeout=30.0
                )
                
                raw_json = json.loads(completion.choices[0].message.content)
                
                # 3. Structural Validation (Phase 16)
                try:
                    plan_obj = ExecutionPlan(**raw_json)
                    
                    # Final Internal Mismatch Check
                    for step in plan_obj.steps:
                        if step.tool not in allowed_tool_names:
                            logger.error(f"❌ Registry Violation in Planner output: {step.tool}")
                            plan_obj.action = PlannerAction.REGISTRY_VIOLATION
                            plan_obj.steps = []
                    
                    logger.info(f"Generated Validated Plan using {model_tier}: {plan_obj.dict()}")
                    return plan_obj.dict()
                    
                except ValidationError as ve:
                    logger.error(f"❌ Planner Schema Error on {model_tier}: {ve}")
                    if model_tier == settings.GROQ_PLANNING_MODEL:
                        continue # Try fallback tier
                    break # Already at lowest tier

            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "rate limit" in error_str:
                    token_budget.report_429(model_tier, str(e))
                    continue # Try fallback tier
                logger.error(f"Planning failed on {model_tier}: {e}")
                if model_tier == settings.GROQ_PLANNING_MODEL:
                    continue # Try fallback
                break

        # Final Fallback Plan (Total failure)
        return {
            "query_analysis": "Critical system failure during planning.",
            "action": "refuse",
            "steps": [],
            "final_instruction": "System unavailable. Suggesting retry later."
        }

planner = Planner()

planner = Planner()
