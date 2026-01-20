from typing import List, Dict, Optional
from app.db.chroma import get_collection
from app.services.embedder import embedder
from app.services.cache import redis_cache
from sentence_transformers import CrossEncoder

class RetrieverService:
    def __init__(self):
        self.collection = get_collection()
        # Initialize CrossEncoder for reranking
        # MS MARCO MiniLM is a great balance of speed/performance
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2') 

    async def retrieve(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        # 1. Check Query Cache
        cached = redis_cache.get_query_cache(query)
        if cached:
             return cached['chunks']

        # 2. Multi-Query Expansion
        from app.services.generator import generator
        queries = await generator.generate_queries(query)
        print(f"Expanding retrieval with queries: {queries}")

        all_candidates = []
        seen_ids = set()
        where_clause = filters if filters else {}

        # 3. Aggregated Dense Retrieval (ChromaDB)
        for q in queries:
            query_embedding = await embedder.aembed_text(q)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2, # Smaller k per query to avoid noise
                where=where_clause if where_clause else None
            )
            
            ids = results['ids'][0]
            documents = results['documents'][0]
            metadatas = results['metadatas'][0]
            distances = results['distances'][0]
            
            for i in range(len(ids)):
                if ids[i] not in seen_ids:
                    all_candidates.append({
                        'id': ids[i],
                        'text': documents[i],
                        'metadata': metadatas[i],
                        'initial_score': 1 - distances[i]
                    })
                    seen_ids.add(ids[i])

        if not all_candidates:
            return []

        # 4. Reranking (Cross-Encoder)
        # Pair original query with each candidate text
        pairs = [[query, doc['text']] for doc in all_candidates]
        scores = self.reranker.predict(pairs)
        
        for i, doc in enumerate(all_candidates):
            doc['score'] = float(scores[i])
        
        # Sort by Reranker score (descending)
        all_candidates.sort(key=lambda x: x['score'], reverse=True)

        # Take Top K
        final_chunks = all_candidates[:top_k]

        # 5. Cache Results
        redis_cache.set_query_cache(query, {'chunks': final_chunks})
        
        return final_chunks

retriever = RetrieverService()
