import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.retriever import retriever
from app.db.postgres import init_db, SessionLocal
from app.db import models

async def verify_hybrid_search():
    print("\n--- Verifying Hybrid Search ---")
    
    # query that might benefit from hybrid (specific keyword)
    query = "External enhancements for LLMs using technique"
    
    print(f"Query: {query}")
    results = await retriever.retrieve(query, top_k=3)
    
    print(f"Retrieved {len(results)} chunks.")
    for i, res in enumerate(results):
        print(f"\nResult {i+1}:")
        print(f"  Source: {res.get('source', 'Unknown')}")
        print(f"  Score: {res.get('score', 0):.4f}")
        print(f"  Text: {res['text'][:100]}...")
        print(f"  Keywords: {res['metadata'].get('keywords', [])}")

if __name__ == "__main__":
    # Ensure DB is initialized
    init_db()
    asyncio.run(verify_hybrid_search())
