import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine

async def main():
    query = "How do I create a Kubernetes Pod?"
    print(f"\nQUERY: {query}")
    print("-" * 40)
    async for update in reasoning_engine.process_query_stream(query):
        u_type = update.get("type")
        if u_type == "status":
             print(f"📡 Status: {update['content']}")
        elif u_type == "plan":
             print(f"📝 Plan: {update['content'].get('action')} with {len(update['content'].get('steps', []))} steps")
        elif u_type == "evaluation":
             print(f"📊 Evaluation: Grade={update['evaluation']['overall_grade']} | Grounding={update['evaluation'].get('metrics', {}).get('grounding_score')}")
        elif u_type == "token":
             print(update.get("content"), end="", flush=True)
        elif u_type == "error":
             print(f"\n❌ Error: {update['content']}")

if __name__ == "__main__":
    asyncio.run(main())
