import sys
import os
import asyncio
import json
from datetime import datetime

# Fix Windows console encoding for emojis
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.ingestion import ingestion_service
from app.services.retriever import get_retriever
from app.services.reasoning_engine import reasoning_engine
from app.db.postgres import SessionLocal
from app.db.models import Document, Chunk

class DetailedLogger:
    """Beautiful logger for detailed pipeline execution tracking."""
    
    def __init__(self, log_file="pipeline_execution_log.md"):
        self.log_file = log_file
        self.start_time = datetime.now()
        self.step_counter = 0
        self.log_entries = []
        
    def header(self, title, level=1):
        """Add a header to the log."""
        prefix = "#" * level
        entry = f"\n{prefix} {title}\n"
        self.log_entries.append(entry)
        print(entry)
        
    def section(self, title):
        """Add a section divider."""
        entry = f"\n{'='*80}\n{title}\n{'='*80}\n"
        self.log_entries.append(entry)
        print(entry)
        
    def subsection(self, title):
        """Add a subsection divider."""
        entry = f"\n{'-'*80}\n{title}\n{'-'*80}\n"
        self.log_entries.append(entry)
        print(entry)
        
    def step(self, description):
        """Log a step with counter."""
        self.step_counter += 1
        entry = f"\n**Step {self.step_counter}**: {description}\n"
        self.log_entries.append(entry)
        print(entry)
        
    def info(self, key, value):
        """Log key-value information."""
        entry = f"- **{key}**: {value}\n"
        self.log_entries.append(entry)
        print(entry, end="")
        
    def code_block(self, content, language=""):
        """Log a code block."""
        entry = f"\n```{language}\n{content}\n```\n"
        self.log_entries.append(entry)
        print(entry)
        
    def json_block(self, data, title=""):
        """Log JSON data beautifully."""
        if title:
            self.log_entries.append(f"\n**{title}**:\n")
            print(f"\n**{title}**:")
        json_str = json.dumps(data, indent=2, ensure_ascii=False)
        self.code_block(json_str, "json")
        
    def success(self, message):
        """Log success message."""
        entry = f"✅ {message}\n"
        self.log_entries.append(entry)
        print(entry, end="")
        
    def warning(self, message):
        """Log warning message."""
        entry = f"⚠️  {message}\n"
        self.log_entries.append(entry)
        print(entry, end="")
        
    def error(self, message):
        """Log error message."""
        entry = f"❌ {message}\n"
        self.log_entries.append(entry)
        print(entry, end="")
        
    def save(self):
        """Save log to file."""
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"# RAG Pipeline Execution Log\n")
            f.write(f"**Generated**: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Duration**: {(datetime.now() - self.start_time).total_seconds():.2f} seconds\n")
            f.writelines(self.log_entries)
        print(f"\n📝 Log saved to: {self.log_file}")

async def detailed_test():
    logger = DetailedLogger()
    
    logger.section("PRODUCTION RAG PIPELINE - DETAILED EXECUTION LOG")
    logger.info("Test Started", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    logger.info("Test Document", "Kubernetes-for-Beginners.pdf")
    
    # ============================================================================
    # PHASE 1: DOCUMENT INGESTION
    # ============================================================================
    logger.header("Phase 1: Document Ingestion & Structure-Aware Chunking", 2)
    
    test_file = "uploads/Kubernetes-for-Beginners.pdf"
    
    if not os.path.exists(test_file):
        logger.error(f"Test file not found: {test_file}")
        return
    
    logger.step("Calculate file hash for deduplication")
    import hashlib
    with open(test_file, 'rb') as f:
        file_content = f.read()
        file_hash = hashlib.md5(file_content).hexdigest()
    
    logger.info("File Size", f"{len(file_content):,} bytes")
    logger.info("MD5 Hash", file_hash)
    
    filename = os.path.basename(test_file)
    
    logger.step("Check if document already exists in database")
    db = SessionLocal()
    try:
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc and existing_doc.status == 'completed':
            logger.success(f"Document already processed (ID: {existing_doc.id})")
            doc_id = existing_doc.id
            chunks_created = existing_doc.chunk_count or 0
        else:
            if existing_doc:
                logger.warning(f"Found stale document in '{existing_doc.status}' state. Deleting and re-processing.")
                db.delete(existing_doc)
                db.commit()
            
            logger.step("Create new document record")
            new_doc = Document(
                filename=filename,
                file_hash=file_hash,
                status="processing"
            )
            db.add(new_doc)
            db.commit()
            db.refresh(new_doc)
            logger.success(f"Document record created (ID: {new_doc.id})")
            
            logger.step("Process document with Smart PDF Processor")
            logger.info("Processing Steps", "Extract text → Detect structure → Generate chunks → Enrich metadata")
            
            ingestion_service.process_document(test_file, filename, file_hash, db)
            
            db.refresh(new_doc)
            doc_id = new_doc.id
            chunks_created = new_doc.chunk_count or 0
            
        logger.success("Ingestion Complete!")
        logger.info("Document ID", doc_id)
        logger.info("Chunks Created", chunks_created)
    finally:
        db.close()
    
    # ============================================================================
    # PHASE 2: DATABASE VERIFICATION
    # ============================================================================
    logger.header("Phase 2: Hybrid Database Verification", 2)
    
    logger.step(f"Query SQLite for document metadata (ID: {doc_id})")
    db = SessionLocal()
    try:
        # FIX: Query by ID instead of filename to ensure consistency with Phase 1
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            logger.success(f"Document found in SQLite")
            logger.info("ID", doc.id)
            logger.info("Status", doc.status)
            logger.info("Chunk Count", doc.chunk_count)
            
            logger.step("Retrieve sample chunks with enriched metadata")
            chunks = db.query(Chunk).filter(Chunk.document_id == doc.id).limit(3).all()
            
            for i, chunk in enumerate(chunks[:3], 1):
                logger.subsection(f"Chunk {i} Details")
                logger.info("Vector ID", chunk.vector_id)
                logger.info("Content Length", f"{len(chunk.content)} characters")
                logger.info("Summary", chunk.summary[:150] + "..." if len(chunk.summary) > 150 else chunk.summary)
                logger.info("Keywords", ", ".join(chunk.keywords[:8]))
                logger.info("Questions", f"{len(chunk.questions)} generated")
                if chunk.questions:
                    for q_idx, question in enumerate(chunk.questions[:2], 1):
                        logger.info(f"  Q{q_idx}", question)
        else:
            logger.error(f"Document ID {doc_id} not found in database")
            return
    finally:
        db.close()
    
    # ============================================================================
    # PHASE 3: REASONING ENGINE ORCHESTRATION (MULTI-QUERY)
    # ============================================================================
    logger.header("Phase 3: Reasoning Engine Feedback Loop & Retrieval Test", 2)
    
    # "Logic Trap": Distroless containers have no shell.
    # Naive Answer: "docker exec -it ... /bin/bash" (FAIL)
    # Correct Answer: "kubectl debug" or "ephemeral containers" (PASS)
    complex_query = "How can I run 'kubectl exec -it <pod> -- /bin/bash' into a distroless container that explicitly has no shell installed?"
    
    logger.section(f"TEST QUESTION: {complex_query}")
    logger.info("Goal", "Trigger feedback loop by asking a constraint-heavy question")
    
    questions = [complex_query]
    
    for q_idx, complex_query in enumerate(questions, 1):
        logger.section(f"QUESTION {q_idx}: {complex_query}")
        
        # FIX: Retrieval Verification moved INSIDE loop for relevance
        logger.step(f"Verifying Retrieval for Question {q_idx}")
        logger.info("Query", complex_query)
        logger.info("Retrieval Strategy", "Dense (ChromaDB) + Keyword (SQLite) + Reranking")
        
        try:
            results = await get_retriever().retrieve(complex_query, top_k=3)
            logger.success(f"Retrieved {len(results)} chunks")
            
            for i, result in enumerate(results[:3], 1):
                logger.subsection(f"Retrieved Chunk {i}")
                logger.info("Relevance Score", f"{result.get('score', 0):.4f}")
                logger.info("Source", result.get('source', 'N/A'))
                logger.info("Text Preview", result['text'][:200] + "...")
        except Exception as e:
            logger.error(f"Retrieval verification failed: {e}")
        
        logger.step(f"Initialize Reasoning Engine for Question {q_idx}")
        logger.info("Pipeline", "Security → Planning → Execution → Routing → Generation → Evaluation")
        
        try:
            logger.subsection("Streaming Pipeline Updates")
            
            token_count = 0
            final_response = ""
            plan_data = None
            eval_data = None
            security_data = None
            
            async for update in reasoning_engine.process_query_stream(complex_query):
                update_type = update.get("type")
                
                if update_type == "security":
                    security_data = update.get("assessment", {})
                    logger.step("Security Check (Stress Testing)")
                    logger.info("Status", "SAFE" if security_data.get('is_safe') else "BLOCKED")
                    if not security_data.get('is_safe'):
                        logger.warning(f"Threat Detected: {security_data.get('threat_detected')}")
                        logger.info("Reasoning", security_data.get('reasoning'))
                    else:
                        logger.success("No threats detected")
                
                elif update_type == "status":
                    status_msg = update.get('content')
                    logger.info("Status Update", status_msg)
                
                elif update_type == "plan":
                    plan_data = update.get("content", {})
                    logger.step("Query Planning (LLM-Powered)")
                    logger.info("Query Analysis", plan_data.get('query_analysis', 'N/A'))
                    logger.info("Total Steps", len(plan_data.get('steps', [])))
                    
                    for step in plan_data.get('steps', []):
                        logger.subsection(f"Step {step.get('step_id')}")
                        logger.info("Tool", step.get('tool'))
                        logger.info("Input", step.get('input'))
                        logger.info("Reason", step.get('reason'))
                    
                    logger.info("Final Instruction", plan_data.get('final_instruction', 'N/A'))
                
                elif update_type == "step_result":
                    logger.success("Step execution completed")
                
                elif update_type == "token":
                    token = update.get("content", "")
                    final_response += token
                    token_count += 1
                    if token_count == 1:
                        logger.step("Response Generation (Streaming)")
                        logger.subsection("Generated Response")
                    print(token, end="", flush=True)
                
                elif update_type == "evaluation":
                    print("\n")  # New line after streaming
                    eval_data = update.get("evaluation", {})
                    metrics = update.get("metrics", {})
                    
                    logger.step("Response Evaluation (LLM Judge)")
                    logger.json_block(eval_data.get('scores', {}), "Quality Scores")
                    logger.info("Overall Grade", eval_data.get('overall_grade', 'N/A'))
                    logger.info("Reasoning", eval_data.get('reasoning', 'N/A'))
                    logger.info("Latency", metrics.get('latency_ms', 'N/A'))
                    logger.info("Estimated Cost", metrics.get('estimated_cost', 'N/A'))
                    logger.info("Grounding Score", metrics.get('grounding_score', 'N/A'))
                
                elif update_type == "complete":
                    logger.success(f"Pipeline execution for Question {q_idx} complete!")
            
            # ============================================================================
            # QUESTION SUMMARY
            # ============================================================================
            logger.header(f"Summary for Question {q_idx}", 2)
            logger.info("Total Tokens Streamed", token_count)
            logger.info("Response Length", f"{len(final_response)} characters")
            logger.info("Final Grade", eval_data.get('overall_grade') if eval_data else 'N/A')
            
            logger.subsection("Complete Response")
            logger.code_block(final_response, "markdown")
            
        except Exception as e:
            logger.error(f"Reasoning Engine failed for Q{q_idx}: {e}")
            import traceback
            traceback.print_exc()
    
    # ============================================================================
    # STEP 5: STRICT GROUNDING TEST (NEGATIVE CONSTRAINT)
    # ============================================================================
    logger.header("Step 5: Strict Grounding Test (Negative Constraint)", 2)
    neg_query = "What is the recipe for chocolate cake?"
    logger.section(f"TEST QUESTION: {neg_query}")
    logger.info("Goal", "Verify model refuses to answer off-topic questions")
    
    neg_response = ""
    async for update in reasoning_engine.process_query_stream(neg_query):
         if update.get("type") == "token":
             neg_response += update.get("content", "")
    
    logger.subsection("Generated Response")
    logger.code_block(neg_response, "markdown")
    
    # Accept various refusal patterns
    refusal_keywords = ["cannot", "unable", "sorry", "not in the context", "provided documents", "I don't know"]
    is_refusal = any(keyword in neg_response.lower() for keyword in refusal_keywords)
    
    if is_refusal:
         logger.success("PASSED: Strict grounding enforced (Refusal detected).")
    else:
         logger.error("FAILED: Model hallucinated an answer.")

    logger.section("TEST COMPLETE")
    logger.success("All steps processed successfully!")
    logger.save()

if __name__ == "__main__":
    asyncio.run(detailed_test())
