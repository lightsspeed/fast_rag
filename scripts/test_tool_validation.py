import asyncio
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine
from app.services.planner import planner

async def test_tool_validation():
    print("="*60)
    print("TESTING TOOL REGISTRY VALIDATION (PHASE 14)")
    print("="*60)

    # Mocking Retriever and Planner using patch
    # We patch app.services.retriever.get_retriever because it's imported locally in ReasoningEngine methods
    with patch("app.services.retriever.get_retriever") as mock_get_retriever:
        
        mock_retriever = AsyncMock()
        mock_retriever.retrieve = AsyncMock(return_value=[{"text": "mock context", "score": 0.9, "dense_score": 0.9}])
        mock_get_retriever.return_value = mock_retriever

        # Mocking Planner to return an INVALID tool name
        original_create_plan = planner.create_plan
        planner.create_plan = AsyncMock(return_value={
            "query_analysis": "Mock analysis",
            "action": "execute",
            "steps": [
                {
                    "step_id": 1,
                    "tool": "document_retriever",
                    "input": "Kubernetes Pods",
                    "reason": "Hallucinated name"
                }
            ],
            "final_instruction": "Synthesize based on phantom retrieval."
        })

        try:
            print("\n[Test 1] Forcing Hallucinated Tool: 'document_retriever'")
            
            async for update in reasoning_engine.process_query_stream("Explain Pods"):
                if update["type"] == "status":
                    print(f"Status: {update['content']}")
                elif update["type"] == "plan":
                    print(f"Plan received with tools: {[s['tool'] for s in update['content']['steps']]}")
                elif update["type"] == "evaluation":
                    # If retries finish, we'll see evaluation
                    print(f"Final Evaluation Grade: {update['evaluation']['overall_grade']}")

            print("\n✅ Verification complete.")
            
        finally:
            planner.create_plan = original_create_plan

if __name__ == "__main__":
    asyncio.run(test_tool_validation())
