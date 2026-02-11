from typing import List, Dict, Any, AsyncGenerator
from app.services.planner import planner
from app.services.tool_executor import tool_executor
from app.services.conditional_router import conditional_router
from app.services.stress_tester import stress_tester
from app.services.human_validation import human_validation
from app.services.evaluator import response_evaluator
from app.services.multi_agent_system import multi_agent_system
from app.services.telemetry import telemetry
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class ReasoningEngine:
    """The central orchestration layer for the production RAG architecture."""
    
    def __init__(self):
        self.MAX_RETRIES = 2 # Increased to allow for validation retry

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Main entry point for processing a user query through the production pipeline."""
        start_time = telemetry.start_timer()
        logger.info(f"Reasoning Engine started for: {query}")
        
        # 1. Stress Testing (Red Teaming)
        stress_assessment = await stress_tester.inspect_query(query)
        if not stress_assessment["is_safe"]:
            return {
                "error": "Security Block",
                "reason": stress_assessment["reasoning"],
                "threat": stress_assessment["threat_detected"]
            }
            
        # 2. Human Validation (Gatekeeper)
        if human_validation.check_necessity(query, stress_assessment):
            await human_validation.validate(query)
            
        current_critique = None
        final_attempt_data = {}
        grounding_score = 0.0
        evaluation = {"overall_grade": "Fail", "reasoning": "No valid plan generated."}
        final_response = "I encountered an internal error during planning."
        results = []

        # Feedback Loop
        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                logger.info(f"RETRACTING: Feedback loop triggered for attempt {attempt}")

            # Circuit Breaker Awareness (Phase 15)
            from app.core.rate_limiter import token_budget
            active_models = {
                "Planning": settings.GROQ_PLANNING_MODEL if token_budget.can_use(settings.GROQ_PLANNING_MODEL) else settings.GROQ_FAST_MODEL,
                "Fast_Tier": settings.GROQ_FAST_MODEL if token_budget.can_use(settings.GROQ_FAST_MODEL) else "Locked"
            }
            logger.info(f"Control Plane - Budget Awareness: {active_models}")

            # 3. Control Plane: Intent Classification & Tool Gating
            from app.services.query_classifier import query_classifier
            intent = query_classifier.classify_query(query)
            
            tools_list = [
                '1. "hybrid_retriever": Search across Vector DB (semantic) and Relational DB (keywords). Use this for internal document knowledge.',
                '2. "web_search": Search the live internet. Use this for real-time info or if internal documents are insufficient.',
                '3. "summarizer": Generate summaries for retrieved content.'
            ]
            
            requires_computation = intent.get("requires_computation", False)
            if requires_computation or intent.get("requires_external_execution", False):
                tools_list.append('4. "code_interpreter": Execute Python code for calculations, data analysis, or logic.')
            
            # Extract names for dynamic validation
            import re
            allowed_tool_names = set(re.findall(r'"([^"]+)"', "\n".join(tools_list)))
            available_tools_str = "\n".join(tools_list)

            # 4. Control Plane: Retrieval Sufficiency Gate
            if not requires_computation:
                from app.services.retriever import get_retriever
                try:
                    pre_check_chunks = await get_retriever().retrieve(query, top_k=1)
                    if not pre_check_chunks:
                         return {"error": "Insufficient Context", "response": "The provided documents do not contain relevant information."}
                        
                    top_score = pre_check_chunks[0].get('score', pre_check_chunks[0].get('dense_score', 0))
                    # Increased to 0.75 for strictness
                    if top_score < 0.75:
                         return {"error": "Insufficient Context", "response": "The provided documents do not contain relevant information."}
                except Exception as e:
                    logger.error(f"Retrieval Gate Critical Error: {e}")
                    return {"error": "Retrieval system unavailable", "response": str(e)}

            # 5. Planning
            plan = await planner.create_plan(query, available_tools_str, critique=current_critique)
            
            # 4.5 Plan & Tool Validation (Phase 14 + Hardening)
            plan_action = plan.get("action", "execute")
            
            if plan_action == "refuse":
                logger.warning(f"⛔ Control Plane: Planner refused query: {plan.get('final_instruction')}")
                return {"error": "Refusal", "response": plan.get("final_instruction", "I cannot fulfill this request.")}
            
            if plan_action == "registry_violation":
                logger.warning("⚠️ Control Plane: Planner reported Registry Violation.")
                if attempt == self.MAX_RETRIES:
                    return {"error": "Planning Exhausted", "response": "Repeated registry violations. Check tool configuration."}
                current_critique = f"Your previous plan failed: Registry Violation. You MUST use ONLY tool names from the provided JSON list."
                continue

            if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
                logger.error("❌ Control Plane: Planner produced invalid JSON structure.")
                current_critique = "Your previous response was not a valid plan JSON object with a 'steps' list."
                continue

            invalid_tools = []
            for step in plan.get("steps", []):
                t_name = step.get("tool")
                if t_name not in allowed_tool_names:
                    invalid_tools.append(t_name)
                # Input safety: must be string
                if not isinstance(step.get("input"), str):
                    logger.warning(f"⚠️ Invalid input type for tool {t_name}")
                    invalid_tools.append(f"{t_name}(invalid_input_type)")

            if invalid_tools:
                logger.warning(f"⚠️ Control Plane: Invalid plan detected: {invalid_tools}")
                if attempt == self.MAX_RETRIES:
                    return {"error": "Planning Exhausted", "response": f"Repeatedly produced invalid tools or inputs: {invalid_tools}"}
                current_critique = f"Your previous plan used unknown or malformed tools: {invalid_tools}. You MUST use ONLY: {list(allowed_tool_names)} and ensure 'input' is a string."
                continue

            # 6. Execution
            results = []
            for step in plan.get("steps", []):
                res = await tool_executor.execute_step(step)
                results.append(res)
                
            # 5. Routing
            next_destination = conditional_router.route(plan, results)
            
            # 6. Specialized Processing (Multi-Agent or Generator)
            if next_destination == "multi_agent_system":
                final_response = "Multi-Agent System handled this query."
            else:
                from app.services.generator import generator
                final_response = await generator.generate(query, results)

            # 7. Evaluation (LLM Judge)
            evaluation = await response_evaluator.evaluate(query, final_response, results)
            
            # Calculate Grounding Score
            from app.services.generator import generator
            grounding_score = generator.calculate_grounding_score(final_response, results)
            
            # 7.1 Decision Layer: Grounding Enforcement
            # Early Abort: Grounding < 0.3 is catastrophic failure
            if grounding_score < 0.3:
                logger.error(f"❌ Catastrophic Grounding Failure ({grounding_score}). Aborting pipeline.")
                evaluation["overall_grade"] = "Fail"
                evaluation["reasoning"] = f"Aborted due to critical grounding failure ({grounding_score})."
                break

            if grounding_score < 0.60:
                logger.warning(f"Grounding Score detection ({grounding_score}) below threshold (0.60). Marking as FAIL.")
                evaluation["overall_grade"] = "Fail"
                evaluation["reasoning"] += f" [System Critique: Low grounding score ({grounding_score}). Response may be hallucinated.]"
            
            final_attempt_data = {
                "query": query,
                "plan": plan,
                "results": results,
                "response": final_response,
                "evaluation": evaluation,
                "security": stress_assessment,
                "attempts": attempt + 1
            }

            # Check if we need to loop back
            if evaluation.get("overall_grade") == "Pass" or attempt >= self.MAX_RETRIES:
                break
            
            current_critique = evaluation.get("reasoning", "The previous response was insufficient.")

        # 8. Performance Metrics
        latency = telemetry.stop_timer(start_time)
        final_attempt_data["evaluation"]["metrics"] = {
            "latency_ms": f"{latency:.2f}ms",
            "estimated_cost": f"${0.00012 * (attempt + 1):.5f}" # Scaling cost by attempts
        }
        
        return final_attempt_data

    async def process_query_stream(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Orchestrates the pipeline and yields detailed progress and final response tokens."""
        start_time = telemetry.start_timer()
        
        # 1. Security Check
        stress_assessment = await stress_tester.inspect_query(query)
        yield {"type": "security", "assessment": stress_assessment}
        
        if not stress_assessment["is_safe"]:
            yield {"type": "error", "content": f"Security Block: {stress_assessment['reasoning']}"}
            return

        current_critique = None
        grounding_score = 0.0
        evaluation = {"overall_grade": "Fail", "reasoning": "No valid plan generated."}
        results = []
        final_response = ""

        # Feedback Loop
        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                yield {"type": "status", "content": f"🔄 Quality check failed. Re-planning attempt {attempt+1}..."}
                logger.info(f"RETRACTING: Streaming feedback loop triggered for attempt {attempt}")

            # Circuit Breaker Awareness (Phase 15)
            from app.core.rate_limiter import token_budget
            active_models = {
                "Planning": settings.GROQ_PLANNING_MODEL if token_budget.can_use(settings.GROQ_PLANNING_MODEL) else settings.GROQ_FAST_MODEL,
                "Fast_Tier": settings.GROQ_FAST_MODEL if token_budget.can_use(settings.GROQ_FAST_MODEL) else "Locked"
            }
            logger.info(f"Control Plane - Budget Awareness: {active_models}")
            yield {"type": "status", "content": f"Control Plane: Budget healthy. Ready for {active_models['Planning']} tier." if active_models['Planning'] == settings.GROQ_PLANNING_MODEL else f"Control Plane: Failover active. Using {active_models['Planning']} tier."}

            # 2. Control Plane: Intent Classification & Tool Gating (Phase 11)
            from app.services.query_classifier import query_classifier
            intent = query_classifier.classify_query(query)
            logger.info(f"Control Plane - Query Intent: {intent}")
            
            # 2a. Dynamic Tool Construction
            tools_list = [
                '1. "hybrid_retriever": Search across Vector DB (semantic) and Relational DB (keywords). Use this for internal document knowledge.',
                '2. "web_search": Search the live internet. Use this for real-time info or if internal documents are insufficient.',
                '3. "summarizer": Generate summaries for retrieved content.'
            ]
            
            requires_computation = intent.get("requires_computation", False)
            if requires_computation or intent.get("requires_external_execution", False):
                tools_list.append('4. "code_interpreter": Execute Python code for calculations, data analysis, or logic.')
            else:
                logger.info("🚫 Control Plane: 'code_interpreter' RESTRICTED for this query.")
            
            # Extract names for dynamic validation (e.g. "hybrid_retriever")
            import re
            allowed_tool_names = set(re.findall(r'"([^"]+)"', "\n".join(tools_list)))
                
            available_tools_str = "\n".join(tools_list)

            # 3. Control Plane: Retrieval Sufficiency Gate (Phase 13)
            # Only gate if it's a "pure RAG" query (no computation)
            if not requires_computation:
                from app.services.retriever import get_retriever
                
                # Pre-flight retrieval (low cost, cached)
                try:
                    pre_check_chunks = await get_retriever().retrieve(query, top_k=1)
                    if not pre_check_chunks:
                        logger.warning("⛔ Control Plane: No documents found. Returning Refusal.")
                        yield {"type": "error", "content": "The provided documents do not contain relevant information."}
                        return
                        
                    top_score = pre_check_chunks[0].get('score', pre_check_chunks[0].get('dense_score', 0))
                    # Threshold increased to 0.75 for technical corpus strictness
                    if top_score < 0.75:
                        logger.warning(f"⛔ Control Plane: Retrieval Confidence ({top_score:.2f}) < 0.75. Returning Refusal.")
                        yield {"type": "error", "content": "The provided documents do not contain relevant information."}
                        return
                    
                    logger.info(f"✅ Control Plane: Data Sufficient (Score: {top_score:.2f}). Proceeding to Planner.")
                except Exception as e:
                    logger.error(f"Retrieval Gate Critical Error: {e}")
                    # Fail Closed logic: stop if retrieval system is down
                    yield {"type": "error", "content": f"Retrieval system unavailable: {str(e)}"}
                    return

            # 4. Planning
            yield {"type": "status", "content": "Planning execution strategy..."}
            plan = await planner.create_plan(query, available_tools_str, critique=current_critique)
            
            # 4.5 Plan & Tool Validation (Phase 14 + Hardening)
            plan_action = plan.get("action", "execute")
            
            if plan_action == "refuse":
                logger.warning(f"⛔ Control Plane: Planner refused query: {plan.get('final_instruction')}")
                yield {"type": "error", "content": f"Refusal: {plan.get('final_instruction', 'I cannot fulfill this request.')}"}
                return
            
            if plan_action == "registry_violation":
                logger.warning("⚠️ Control Plane: Planner reported Registry Violation.")
                if attempt == self.MAX_RETRIES:
                    yield {"type": "error", "content": "Planning Exhausted: Repeated registry violations."}
                    return
                yield {"type": "status", "content": "⚠️ Plan rejected: Tool Registry Violation. Re-aligning..."}
                current_critique = f"Your previous plan failed: Registry Violation. You MUST use ONLY tool names from the provided JSON list."
                continue

            if not isinstance(plan, dict) or not isinstance(plan.get("steps"), list):
                logger.error("❌ Control Plane: Planner produced invalid JSON structure.")
                current_critique = "Your previous response was not a valid plan JSON object with a 'steps' list."
                continue

            invalid_tools = []
            for step in plan.get("steps", []):
                t_name = step.get("tool")
                if t_name not in allowed_tool_names:
                    invalid_tools.append(t_name)
                # Input safety: must be string
                if not isinstance(step.get("input"), str):
                    logger.warning(f"⚠️ Invalid input type for tool {t_name}")
                    invalid_tools.append(f"{t_name}(invalid_input_type)")

            if invalid_tools:
                logger.warning(f"⚠️ Control Plane: Invalid plan detected: {invalid_tools}")
                if attempt == self.MAX_RETRIES:
                    yield {"type": "error", "content": f"Planning Exhausted: Repeatedly produced invalid tools or inputs {invalid_tools}."}
                    return
                yield {"type": "status", "content": f"⚠️ Plan rejected: Invalid tools or inputs {invalid_tools} used. Re-aligning..."}
                current_critique = f"Your previous plan used unknown or malformed tools: {invalid_tools}. You MUST use ONLY: {list(allowed_tool_names)} and ensure 'input' is a string."
                continue

            yield {"type": "plan", "content": plan}

            # 3. Execution
            results = []
            for step in plan.get("steps", []):
                yield {"type": "status", "content": f"Executing: {step['reason']}"}
                res = await tool_executor.execute_step(step)
                results.append(res)
                yield {"type": "step_result", "content": res}

            # 4. Routing
            next_destination = conditional_router.route(plan, results)
            yield {"type": "status", "content": f"Routing to: {next_destination}"}

            # 5. Final Generation (Streaming)
            final_response = ""
            if next_destination == "multi_agent_system":
                async for token in multi_agent_system.execute_task_stream(query, results):
                    final_response += token
                    yield {"type": "token", "content": token}
            else:
                # Simple Synthesis Fallback
                from app.services.generator import generator
                async for token in generator.generate_stream(query, results):
                    final_response += token
                    yield {"type": "token", "content": token}

            # 6. Evaluation (Trigger loop)
            evaluation = await response_evaluator.evaluate(query, final_response, results)
            
            # Calculate Grounding Score
            from app.services.generator import generator
            grounding_score = generator.calculate_grounding_score(final_response, results)
            
            # 7.1 Decision Layer: Grounding Enforcement
            # Early Abort: Grounding < 0.3 is catastrophic failure
            if grounding_score < 0.3:
                logger.error(f"❌ Catastrophic Grounding Failure ({grounding_score}). Aborting pipeline.")
                evaluation["overall_grade"] = "Fail"
                evaluation["reasoning"] = f"Aborted due to critical grounding failure ({grounding_score})."
                break

            if grounding_score < 0.60:
                logger.warning(f"Grounding Score detection ({grounding_score}) below threshold (0.60). Marking as FAIL.")
                evaluation["overall_grade"] = "Fail"
                evaluation["reasoning"] += f" [System Critique: Low grounding score ({grounding_score}). Response may be hallucinated.]"
            
            if evaluation.get("overall_grade") == "Pass" or attempt >= self.MAX_RETRIES:
                break
            
            current_critique = evaluation.get("reasoning", "Poor quality detected.")
            
        latency = telemetry.stop_timer(start_time)
        
        # Structure metrics
        metrics = {
            "latency_ms": f"{latency:.2f}ms",
            "estimated_cost": f"${0.00015 * (attempt + 1):.5f}",
            "grounding_score": grounding_score
        }
        
        yield {
            "type": "evaluation", 
            "evaluation": evaluation,
            "metrics": metrics
        }
        yield {"type": "complete"}

reasoning_engine = ReasoningEngine()
