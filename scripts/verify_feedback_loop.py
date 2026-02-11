import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine

async def verify_feedback_loop():
    print("\n--- Verifying Evaluation Feedback Loop ---")
    
    # query designed to test retrieval and synthesis quality
    query = "Explain exactly how the structure-aware chunking handles nested tables in a PDF."
    
    print(f"User Query: {query}")
    
    # Using non-streaming version to easily check attempts
    output = await reasoning_engine.process_query(query)
    
    print(f"\nFinal Analysis: {output['plan']['query_analysis']}")
    print(f"Total Attempts: {output.get('attempts', 1)}")
    print(f"Evaluation Grade: {output['evaluation']['overall_grade']}")
    print(f"Latency: {output['evaluation']['metrics']['latency_ms']}")
    
    if output.get('attempts', 1) > 1:
        print("\n✅ SUCCESS: Feedback loop was triggered and system self-corrected.")
    else:
        print("\nℹ️ INFO: System produced a passing response on the first try.")

if __name__ == "__main__":
    asyncio.run(verify_feedback_loop())
