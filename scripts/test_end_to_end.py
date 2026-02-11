import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Force UTF-8 output to file
log_file = open('pipeline_execution_log.md', 'w', encoding='utf-8')
sys.stdout = log_file
sys.stderr = log_file

from app.services.ingestion import ingestion_service
from app.services.retriever import get_retriever
from app.services.reasoning_engine import reasoning_engine
from app.db.postgres import SessionLocal
from app.db.models import Document, Chunk

async def test_end_to_end():
    print("\n" + "="*80)
    print("END-TO-END PRODUCTION RAG PIPELINE TEST")
    print("="*80)
    
    # Step 1: Ingestion
    print("\n[STEP 1] DOCUMENT INGESTION & STRUCTURE-AWARE CHUNKING")
    print("-" * 80)
    
    test_file = "uploads/Kubernetes-for-Beginners.pdf"
    
    if not os.path.exists(test_file):
        print(f"❌ Test file not found: {test_file}")
        return
    
    print(f"📄 Processing: {test_file}")
    
    # Calculate file hash
    import hashlib
    with open(test_file, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    filename = os.path.basename(test_file)
    
    # Create database session and document record
    db = SessionLocal()
    try:
        # Check if document already exists
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc:
            print(f"ℹ️  Document already processed (ID: {existing_doc.id})")
            doc_id = existing_doc.id
            chunks_created = existing_doc.chunk_count or 0
        else:
            # Create new document record
            new_doc = Document(
                filename=filename,
                file_hash=file_hash,
                status="processing"
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            
            # Process the document
            ingestion_service.process_document(test_file, filename, file_hash, db)
            
            # Refresh to get updated values
            db.refresh(new_doc)
            doc_id = new_doc.id
            chunks_created = new_doc.chunk_count or 0
            
        print(f"✅ Ingestion Complete!")
        print(f"   - Document ID: {doc_id}")
        print(f"   - Chunks Created: {chunks_created}")
    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        db.close()
        return
    finally:
        db.close()
    
    # Step 2: Verify Database Storage
    print("\n[STEP 2] DATABASE VERIFICATION (Hybrid Storage)")
    print("-" * 80)
    
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.filename == "Kubernetes-for-Beginners.pdf").first()
        if doc:
            print(f"✅ Document found in SQLite: ID={doc.id}, Status={doc.status}")
            
            chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).limit(3).all()
            print(f"✅ Sample Chunks (showing 3/{len(chunks)}):")
            for i, chunk in enumerate(chunks[:3], 1):
                print(f"\n   Chunk {i}:")
                print(f"   - Vector ID: {chunk.vector_id}")
                print(f"   - Summary: {chunk.summary[:100]}...")
                print(f"   - Keywords: {chunk.keywords[:5]}")
        else:
            print("❌ Document not found in database")
            return
    finally:
        db.close()
    
    # Step 3: Hybrid Retrieval Test
    print("\n[STEP 3] HYBRID RETRIEVAL (Vector + Keyword)")
    print("-" * 80)
    
    test_query = "How do I create a Kubernetes deployment?"
    print(f"🔍 Query: {test_query}")
    
    try:
        results = await get_retriever().retrieve(test_query, top_k=3)
        print(f"✅ Retrieved {len(results)} chunks:")
        for i, result in enumerate(results[:3], 1):
            print(f"\n   Result {i}:")
            print(f"   - Score: {result.get('score', 'N/A'):.4f}")
            print(f"   - Source: {result.get('source', 'N/A')}")
            print(f"   - Text Preview: {result['text'][:150]}...")
    except Exception as e:
        print(f"❌ Retrieval failed: {e}")
        return
    
    # Step 4: Reasoning Engine Orchestration
    print("\n[STEP 4] REASONING ENGINE ORCHESTRATION")
    print("-" * 80)
    
    complex_query = "What are the key differences between Pods and Deployments in Kubernetes?"
    print(f"🧠 Complex Query: {complex_query}")
    
    try:
        print("\n📊 Streaming Pipeline Updates:")
        print("-" * 80)
        
        token_count = 0
        final_response = ""
        
        async for update in reasoning_engine.process_query_stream(complex_query):
            update_type = update.get("type")
            
            if update_type == "security":
                assessment = update.get("assessment", {})
                print(f"🔒 Security Check: {assessment.get('is_safe', 'Unknown')}")
                if not assessment.get('is_safe'):
                    print(f"   ⚠️  Threat: {assessment.get('threat_detected')}")
            
            elif update_type == "status":
                print(f"⚙️  Status: {update.get('content')}")
            
            elif update_type == "plan":
                plan = update.get("content", {})
                print(f"\n📋 Execution Plan:")
                print(f"   Analysis: {plan.get('query_analysis', 'N/A')}")
                print(f"   Steps: {len(plan.get('steps', []))}")
                for step in plan.get('steps', [])[:3]:
                    print(f"      - {step.get('tool')}: {step.get('reason')}")
            
            elif update_type == "step_result":
                print(f"✓ Step completed")
            
            elif update_type == "token":
                token = update.get("content", "")
                final_response += token
                token_count += 1
                if token_count == 1:
                    print(f"\n💬 Response Stream:")
                    print("   ", end="")
                print(token, end="", flush=True)
            
            elif update_type == "evaluation":
                print("\n\n📊 Evaluation Metrics:")
                eval_data = update.get("evaluation", {})
                metrics = update.get("metrics", {})
                print(f"   - Grade: {eval_data.get('overall_grade', 'N/A')}")
                print(f"   - Scores: {eval_data.get('scores', {})}")
                print(f"   - Latency: {metrics.get('latency_ms', 'N/A')}")
                print(f"   - Cost: {metrics.get('estimated_cost', 'N/A')}")
            
            elif update_type == "complete":
                print("\n\n✅ Pipeline Complete!")
        
        print("\n" + "="*80)
        print("FINAL RESPONSE SUMMARY")
        print("="*80)
        print(f"Total Tokens Streamed: {token_count}")
        print(f"Response Length: {len(final_response)} characters")
        
    except Exception as e:
        print(f"\n❌ Reasoning Engine failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n" + "="*80)
    print("✅ END-TO-END TEST COMPLETE!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
