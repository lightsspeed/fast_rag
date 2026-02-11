import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine

async def main():
    query = "What is the best recipe for a chocolate cake?"
    print(f"\nQUERY: {query}")
    print("-" * 40)
    async for update in reasoning_engine.process_query_stream(query):
        print(update)

if __name__ == "__main__":
    asyncio.run(main())
