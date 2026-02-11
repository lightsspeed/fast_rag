import asyncio
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine

async def run_test(query: str, test_id: int):
    print("\n" + "="*80)
    print(f" TEST CASE {test_id}: {query}")
    print("="*80)
    
    try:
        async for update in reasoning_engine.process_query_stream(query):
            u_type = update.get("type")
            content = update.get("content") or update.get("assessment") or update.get("evaluation") or update.get("metrics")
            
            if u_type == "security":
                print(f"🛡️  [Security Check] Safe: {content.get('is_safe')} | Threat: {content.get('threat_detected')}")
            elif u_type == "status":
                print(f"📡 [Status] {content}")
            elif u_type == "plan":
                print(f"📝 [Plan] Action: {update['content'].get('action')} | Steps: {len(update['content'].get('steps', []))}")
                for i, step in enumerate(update['content'].get('steps', [])):
                    print(f"    - Step {i+1}: {step['tool']}({step['input']})")
            elif u_type == "step_result":
                # Truncate output for readability
                output = str(update['content'].get('output'))
                print(f"✅ [Result] Tool: {update['content']['tool']} | Size: {len(output)} chars")
            elif u_type == "token":
                print(update.get("content"), end="", flush=True)
            elif u_type == "error":
                print(f"\n❌ [Error] {content}")
            elif u_type == "evaluation":
                print(f"📊 [Evaluation] Grade: {content.get('overall_grade')} | Grounding: {content.get('metrics', {}).get('grounding_score')}")
    except Exception as e:
        print(f"💥 [Crash] {str(e)}")

async def main():
    queries = [
        "How do I create a Kubernetes Pod?",                                # Case 1: Valid RAG
        "What is the best recipe for a chocolate cake?",                    # Case 2: Off-topic (Gate/Refusal)
        "Calculate the sum of all prime numbers between 1 and 20."           # Case 3: Computation (Tool Gating)
    ]
    
    for i, query in enumerate(queries):
        await run_test(query, i+1)

if __name__ == "__main__":
    asyncio.run(main())
