import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.planner import planner
from app.services.query_classifier import query_classifier

async def test_tool_gating():
    print("="*60)
    print("TESTING TOOL GATING LAYER")
    print("="*60)

    # Test Case 1: Conceptual Query (Should DISABLE code_interpreter)
    q1 = "What is a Kubernetes Pod?"
    print(f"\n[Test 1] Query: '{q1}'")
    
    # Check Classifier directly
    classification = query_classifier.classify_query(q1)
    print(f"Classification: {classification}")
    if not classification.get('requires_computation'):
        print("✅ Classifier Correctly flagged requires_computation=False")
    else:
        print("❌ Classifier FAIL: Flagged simple query as computational")

    # Helper to simulate Control Plane tool construction
    def get_tools_str(intent):
        tools_list = [
            '1. "hybrid_retriever": Search across Vector DB (semantic) and Relational DB (keywords). Use this for internal document knowledge.',
            '2. "web_search": Search the live internet. Use this for real-time info or if internal documents are insufficient.',
            '3. "summarizer": Generate summaries for retrieved content.'
        ]
        if intent.get("requires_computation", False) or intent.get("requires_external_execution", False):
            tools_list.append('4. "code_interpreter": Execute Python code for calculations, data analysis, or logic.')
        return "\n".join(tools_list)

    # Check Planner
    tools_str_1 = get_tools_str(classification)
    plan = await planner.create_plan(q1, tools_str_1)
    steps = plan.get('steps', [])
    tools_used = [s.get('tool') for s in steps]
    print(f"Tools Selected: {tools_used}")
    
    if "code_interpreter" not in tools_used:
        print("✅ Gating SUCCESS: code_interpreter NOT used.")
    else:
        print("❌ Gating FAIL: code_interpreter WAS used.")


    # Test Case 2: Computational Query (Should ENABLE code_interpreter)
    q2 = "Calculate the square root of 256 and multiply by 5."
    print(f"\n[Test 2] Query: '{q2}'")
    
    classification = query_classifier.classify_query(q2)
    print(f"Classification: {classification}")
    if classification.get('requires_computation'):
        print("✅ Classifier Correctly flagged requires_computation=True")
    else:
        print("❌ Classifier FAIL: Failed to flag computational query")

    tools_str_2 = get_tools_str(classification)
    plan = await planner.create_plan(q2, tools_str_2)
    steps = plan.get('steps', [])
    tools_used = [s.get('tool') for s in steps]
    print(f"Tools Selected: {tools_used}")
    
    if "code_interpreter" in tools_used:
        print("✅ Gating SUCCESS: code_interpreter used correctly.")
    else:
        print("❌ Gating FAIL: code_interpreter was NOT used.")

if __name__ == "__main__":
    asyncio.run(test_tool_gating())
