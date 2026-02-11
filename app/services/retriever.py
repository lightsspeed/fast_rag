from typing import List, Dict, Optional
from app.db.chroma import get_collection
from app.services.embedder import embedder
from app.services.cache import redis_cache
from sentence_transformers import CrossEncoder
from app.db.postgres import SessionLocal
from app.db.models import Chunk, Document
from sqlalchemy import or_, String

class RetrieverService:
    def __init__(self):
        self.collection = get_collection()
        # Initialize CrossEncoder for reranking
        self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2') 

    async def retrieve(self, query: str, top_k: int = 5, filters: Optional[Dict] = None) -> List[Dict]:
        # 1. Check Query Cache
        cached = redis_cache.get_query_cache(query)
        if cached:
             return cached['chunks']

        # 2. Multi-Query Expansion
        from app.services.generator import generator
        queries = await generator.generate_queries(query)
        print(f"Expanding retrieval with {len(queries)} queries")

        all_candidates = []
        seen_ids = set()
        where_clause = filters if filters else {}

        # 3. Hybrid Retrieval: Dense (ChromaDB) + Keyword (SQLite)
        # 3a. Dense Retrieval
        for q in queries:
            query_embedding = await embedder.aembed_text(q)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k * 2,
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
                        'dense_score': 1 - distances[i],
                        'source': 'dense'
                    })
                    seen_ids.add(ids[i])

        # 3b. Keyword Retrieval (SQLite)
        keyword_results = self._keyword_retrieval(query, top_k=top_k)
        for cand in keyword_results:
            if cand['id'] not in seen_ids:
                all_candidates.append(cand)
                seen_ids.add(cand['id'])
            else:
                # If already found by dense, mark it as hybrid
                for existing in all_candidates:
                    if existing['id'] == cand['id']:
                        existing['source'] = 'hybrid'
                        break

        if not all_candidates:
            return []

        # 4. Reranking (Cross-Encoder)
        pairs = [[query, doc['text']] for doc in all_candidates]
        scores = self.reranker.predict(pairs)
        
        import math
        def sigmoid(x):
            return 1 / (1 + math.exp(-x))

        for i, doc in enumerate(all_candidates):
            doc['score'] = float(sigmoid(scores[i]))
        
        all_candidates.sort(key=lambda x: x['score'], reverse=True)

        # 5. (Removed Implicit Web Search to ensure strict tool gating)
        # Web Search is now an explicit tool for the Planner.
        
        final_chunks = all_candidates[:top_k]

        # 6. Cache Results
        redis_cache.set_query_cache(query, {'chunks': final_chunks})
        
        return final_chunks

    def _keyword_retrieval(self, query: str, top_k: int = 5) -> List[Dict]:
        """Performs keyword-based search in the Relational DB (SQLite)."""
        db = SessionLocal()
        try:
            # Simple keyword matching in content, summary, and keywords
            # For a production app, use FTS5 (SQLite) or tsvector (Postgres)
            search_terms = query.split()
            filters = []
            for term in search_terms:
                if len(term) < 3: continue
                term_filter = or_(
                    Chunk.content.ilike(f"%{term}%"),
                    Chunk.summary.ilike(f"%{term}%"),
                    Chunk.keywords.cast(String).ilike(f"%{term}%")
                )
                filters.append(term_filter)
            
            if not filters:
                return []

            results = db.query(Chunk).filter(or_(*filters)).limit(top_k).all()
            
            candidates = []
            for res in results:
                candidates.append({
                    'id': res.vector_id,
                    'text': res.content,
                    'metadata': {
                        'summary': res.summary,
                        'keywords': res.keywords,
                        'questions': res.questions
                    },
                    'dense_score': 0.5, # Baseline score for keyword matches
                    'source': 'keyword'
                })
            return candidates
        except Exception as e:
            print(f"Keyword retrieval failed: {e}")
            return []
        finally:
            db.close()

_retriever_instance = None

def get_retriever():
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = RetrieverService()
    return _retriever_instance
