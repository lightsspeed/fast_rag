import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reasoning_engine import reasoning_engine

async def test_retrieval_gate():
    print("="*60)
    print("TESTING RETRIEVAL SUFFICIENCY GATE")
    print("="*60)

    # Test Case 1: Nonsense Query (Should Fail Gate)
    # Asking something completely random that shouldn't be in the RAG DB
    q1 = "sflkjsdflkjsdflkjsdf" 
    print(f"\n[Test 1] Query: '{q1}' (Expect Refusal)")

    response = await reasoning_engine.process_query(q1)
    print(f"Response: {response}")

    if response.get("error") == "Insufficient Context":
        print("✅ Gate SUCCESS: Blocked nonsense query.")
    else:
        # It's possible the classifier thought it needed computation? or Retriever found something with score > 0.6?
        # Unlikely for random string.
        print(f"❌ Gate FAIL: Did not return 'Insufficient Context'. Got: {response.get('error', 'Success')}")

    # Test Case 2: Relevant Query (Should Pass Gate)
    q2 = "What is a Kubernetes Pod?"
    print(f"\n[Test 2] Query: '{q2}' (Expect Pass)")
    
    # We expect a normal response structure, OR a security block if 'safe' is false, but definitely not 'Insufficient Context'
    # strict refusal might happen if documents aren't loaded, but let's assume ingest_all.py ran.
    # If DB is empty, this might fail Test 2, but Test 1 is the critical one for this feature.
    
    response = await reasoning_engine.process_query(q2)
    # We just want to ensure it didn't fail the *Gate*.
    if response.get("error") == "Insufficient Context":
        print("❌ Gate FAIL: Blocked relevant query (False Positive) OR DB is empty.")
    else:
        print("✅ Gate SUCCESS: Allowed relevant query.")

if __name__ == "__main__":
    asyncio.run(test_retrieval_gate())
