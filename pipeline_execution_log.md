Redis not available. Using In-Memory Cache.

================================================================================
END-TO-END PRODUCTION RAG PIPELINE TEST
================================================================================

[STEP 1] DOCUMENT INGESTION & STRUCTURE-AWARE CHUNKING
--------------------------------------------------------------------------------
📄 Processing: uploads/Kubernetes-for-Beginners.pdf
ℹ️  Document already processed (ID: 22)
✅ Ingestion Complete!
   - Document ID: 22
   - Chunks Created: 346

[STEP 2] DATABASE VERIFICATION (Hybrid Storage)
--------------------------------------------------------------------------------
✅ Document found in SQLite: ID=20, Status=completed
✅ Sample Chunks (showing 3/0):

[STEP 3] HYBRID RETRIEVAL (Vector + Keyword)
--------------------------------------------------------------------------------
🔍 Query: How do I create a Kubernetes deployment?
Expanding retrieval with 4 queries
✅ Retrieved 3 chunks:

   Result 1:
   - Score: 0.9997
   - Source: dense
   - Text Preview: The template has a POD definition inside it. Once the file is ready run the kubectl create command and specify deployment definition file. Then run th...

   Result 2:
   - Score: 0.9996
   - Source: dense
   - Text Preview: The template has a POD definition inside it. Once the file is ready run the kubectl create command and specify deployment 
definition file. Then run t...

   Result 3:
   - Score: 0.9886
   - Source: dense
   - Text Preview: Depending on the platform you are deploying your Kubernetes cluster on you may use any of these solutions. For example, if you were setting up a kuber...

[STEP 4] REASONING ENGINE ORCHESTRATION
--------------------------------------------------------------------------------
🧠 Complex Query: What are the key differences between Pods and Deployments in Kubernetes?

📊 Streaming Pipeline Updates:
--------------------------------------------------------------------------------
🔒 Security Check: True
Expanding retrieval with 4 queries
⚙️  Status: Planning execution strategy...
📉 CIRCUIT BREAKER: Locking model 'llama-3.3-70b-versatile' for 349.74s due to Rate Limit.
📉 Rate Limit Hit on llama-3.3-70b-versatile. Failing over to llama-3.1-8b-instant immediately.
⚠️ Budget Constraint: llama-3.3-70b-versatile is locked for 349.7s. Downgrading to llama-3.1-8b-instant.

📋 Execution Plan:
   Analysis: N/A
   Steps: 2
      - document_retriever: Retrieve conceptual information about Pod and Deployment definitions.
      - summarizer: Extract and summarize key differences between Pods and Deployments.
⚙️  Status: Executing: Retrieve conceptual information about Pod and Deployment definitions.
Unknown tool: document_retriever
✓ Step completed
⚙️  Status: Executing: Extract and summarize key differences between Pods and Deployments.
✓ Step completed
⚙️  Status: Routing to: generator

💬 Response Stream:
   I cannot answer this based on the provided documents.Grounding Score detection (0.0) below threshold (0.60). Marking as FAIL.
⚙️  Status: 🔄 Quality check failed. Re-planning attempt 2...
⚙️  Status: Planning execution strategy...
⚠️ Budget Constraint: llama-3.3-70b-versatile is locked for 344.1s. Downgrading to llama-3.1-8b-instant.

📋 Execution Plan:
   Analysis: N/A
   Steps: 3
      - hybrid_retriever: Internal document knowledge lookup on Kubernetes concepts
      - summarizer: Summary generated from retrieved information on Kubernetes Deployments and Pods
      - summarizer: Summary generated from retrieved information on Kubernetes Deployments and Pods
⚙️  Status: Executing: Internal document knowledge lookup on Kubernetes concepts
Expanding retrieval with 4 queries
✓ Step completed
⚙️  Status: Executing: Summary generated from retrieved information on Kubernetes Deployments and Pods
✓ Step completed
⚙️  Status: Executing: Summary generated from retrieved information on Kubernetes Deployments and Pods
✓ Step completed
⚙️  Status: Routing to: generator
Based on the provided context [Chunk 1, Chunk 2, Chunk 3], the key differences between Pods and Deployments in Kubernetes are:

* Pods are ephemeral and stateless [Chunk 2], while Deployments are designed for scalability and high availability.
* Pods can be created, updated, or deleted independently [Chunk 3], while Deployments manage the lifecycle of Pods, including rolling updates, undo changes, and pause and resume changes to deployments [Chunk 1].

📊 Evaluation Metrics:
   - Grade: Pass
   - Scores: {'faithfulness': 0.8, 'relevance': 1.0, 'helpfulness': 1.0, 'context_adherence': 1.0}
   - Latency: 19045.29ms
   - Cost: $0.00030


✅ Pipeline Complete!

================================================================================
FINAL RESPONSE SUMMARY
================================================================================
Total Tokens Streamed: 108
Response Length: 508 characters

================================================================================
✅ END-TO-END TEST COMPLETE!
================================================================================
