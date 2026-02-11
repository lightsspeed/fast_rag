import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine
from app.services.multi_agent_system import multi_agent_system

async def verify_reasoning_pipeline():
    print("\n--- Verifying Reasoning Engine & Multi-Agent Flow ---")
    
    query = "How do I set up Kubernetes for beginners using the provided PDFs?"
    
    print(f"User Query: {query}")
    
    # 1. Start Reasoning Engine
    reasoning_output = await reasoning_engine.process_query(query)
    
    print(f"Plan Query Analysis: {reasoning_output['plan']['query_analysis']}")
    print(f"Determined Destination: {reasoning_output['next_destination']}")
    
    # 2. If routed to agents, execute agent flow
    if reasoning_output['next_destination'] == 'multi_agent_system' or True: # Force for verification
        print("\n--- Executing Multi-Agent System (Forced) ---")
        final_answer = await multi_agent_system.execute_task(query, reasoning_output['results'])
        print("\nFinal Multi-Agent Response Preview:")
        print(final_answer[:300] + "...")

if __name__ == "__main__":
    asyncio.run(verify_reasoning_pipeline())
