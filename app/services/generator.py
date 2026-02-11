from groq import Groq
from app.core.config import settings
from typing import List, AsyncGenerator

class GeneratorService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        
        self.system_prompt_template = """You are a highly capable AI specialized in technical troubleshooting and document analysis. Your goal is to provide a comprehensive, in-depth explanation based on the provided context.

Guidelines:
1. **Thorough Answers**: Provide a detailed, step-by-step technical explanation. Always aim for depth and completeness.
2. **NO INLINE CITATIONS**: Do not use citations like "[Chunk 1]" or "[1]" in your response text. Provide a natural, professionally written technical answer. 
3. **Context Adherence**: Answer ONLY using information from the context below. If the context is missing info, state what is missing.
4. **Professional Tone**: Be technical, clear, and professional. 

Context:
{context_chunks}

User Question: {query}

Answer:"""

    async def generate_queries(self, query: str) -> List[str]:
        """Generate 3 variations of the query for multi-query retrieval."""
        from app.core.rate_limiter import groq_rate_limiter, token_budget
        
        # Optimization: Use Fast Model for query expansion
        target_model = settings.GROQ_FAST_MODEL
        
        # Check Budget
        if not token_budget.can_use(target_model):
             # If fast model is locked, we can try the main model or just return original
             if token_budget.can_use(self.model):
                 target_model = self.model
             else:
                 print(f"⚠️ Query Expansion Skipped: All models rate limited.")
                 return [query]

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Generate 3 different search queries based on the user's question to help find more relevant information in a document database. Return only the queries, one per line, without numbers or bullets."},
            {"role": "user", "content": query}
        ]
        try:
            groq_rate_limiter.wait_if_needed()
            completion = self.client.chat.completions.create(
                model=target_model,
                messages=messages,
                temperature=0.5,
                max_tokens=100,
            )
            content = completion.choices[0].message.content.strip()
            # Clean up and split by line
            queries = [q.strip() for q in content.split('\n') if q.strip()]
            # Add original query to be safe
            if query not in queries:
                queries.append(query)
            return queries[:4] # Original + 3 variations
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                token_budget.report_429(target_model, str(e))
                print(f"📉 Query Expansion Rate Limited ({target_model}). Using original query.")
            else:
                print(f"Query generation failed: {e}")
            return [query]

    def _classify_query_type(self, query: str) -> str:
        """Classify query to adjust response style."""
        query_lower = query.lower()
        
        # How-to / Setup questions
        if any(word in query_lower for word in ['how to', 'setup', 'configure', 'install', 'create']):
            return 'howto'
        # Comparison questions
        elif any(word in query_lower for word in ['difference', 'vs', 'compare', 'better']):
            return 'comparison'
        # Explanation questions
        elif any(word in query_lower for word in ['what is', 'explain', 'define', 'meaning']):
            return 'explanation'
        # Troubleshooting
        elif any(word in query_lower for word in ['error', 'issue', 'problem', 'fix', 'debug']):
            return 'troubleshooting'
        else:
            return 'general'

    async def generate_stream(self, query: str, context_chunks: List[dict]) -> AsyncGenerator[str, None]:
        # Handle different chunk formats (from retriever vs tool executor)
        formatted_chunks = []
        for i, chunk in enumerate(context_chunks):
            if isinstance(chunk, dict):
                # Try different possible keys
                text = chunk.get('text') or chunk.get('output') or chunk.get('content') or str(chunk)
                formatted_chunks.append(f"[Chunk {i+1}]\n{text}")
        
        context_text = "\n\n".join(formatted_chunks) if formatted_chunks else "No context available."
        
        query_type = self._classify_query_type(query)
        
        # Adjust instructions based on query type
        style_guidance = {
            'howto': "Focus on step-by-step instructions and practical examples. Include prerequisites if mentioned in context.",
            'comparison': "Present both sides clearly. Use a balanced structure highlighting key differences.",
            'explanation': "Provide a clear conceptual overview first, then dive into details.",
            'troubleshooting': "Start with the most likely solution. Provide debugging steps if available.",
            'general': "Answer directly and comprehensively."
        }
        
        system_instructions = f"""You are a strict, context-aware AI assistant.
        
**CORE DIRECTIVE: YOU MUST ANSWER REQUIRED QUESTIONS USING *ONLY* THE PROVIDED CONTEXT.**

1. **NO OUTSIDE KNOWLEDGE**: Do not use prior knowledge, training data, or external facts. If the answer is not in the context, say: "I cannot answer this based on the provided documents."
2. **STRICT CITATIONS**: Every claim must be backed by a citation [Chunk X].
   - Bad: "Pods are valid."
   - Good: "Pods are the smallest deployable units [Chunk 1]."
3. **NO HALLUCINATIONS**: Do not make up facts to fill gaps.
4. **Professional Tone**: Be technical and precise.

**Context:**
{context_text}"""
        
        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": query}
        ]

        from app.core.rate_limiter import groq_rate_limiter, token_budget
        
        # Determine model
        target_model = self.model
        if not token_budget.can_use(target_model):
             # If our default model is locked, we technically have no fallback defined for Generator 
             # (unless we fallback to a DIFFERENT fast model, but we only have one Groq key/model set usually).
             # For now, we'll log it and try anyway (maybe the lock is for Planner's 70b?).
             # Actually, if we are using 8b and it's locked, we are stuck. 
             # BUT, if we upgrade Generator to use 70b for "Complex" queries later, this logic helps.
             # Let's assume we stick to self.model for now, but handle the 429 reporting.
             pass

        try:
            groq_rate_limiter.wait_if_needed()
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1, # Lowest temp for strict adherence
                max_tokens=1500,
                top_p=0.95,
                stream=True,
                stop=None,
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                token_budget.report_429(self.model, str(e))
                yield f"[System Error] Rate limit exceeded for {self.model}. Please try again later."
            else:
                yield f"[System Error] Generation failed: {e}"

    async def generate(self, query: str, context_chunks: List[dict]) -> str:
        """Non-streaming version of generate_stream."""
        from app.core.rate_limiter import groq_rate_limiter, token_budget
        
        # Determine model & check budget
        target_model = self.model
        if not token_budget.can_use(target_model):
            # No fallback yet for generator, but we'll report
            pass

        # We reuse the logic but collect tokens manually if we don't want to duplicate system instructions
        # Or better: refactor the instructions out. For now, let's keep it simple.
        full_text = ""
        async for token in self.generate_stream(query, context_chunks):
            if token.startswith("[System Error]"):
                return token
            full_text += token
        
        return full_text

    def calculate_grounding_score(self, response: str, context_chunks: List[dict]) -> float:
        """
        Calculates the grounding score: % of significant response tokens present in the context.
        """
        try:
            if not response or not context_chunks:
                return 0.0
                
            # 1. Prepare Context Text
            context_parts = []
            for chunk in context_chunks:
                 val = chunk.get('text') or chunk.get('output') or chunk.get('content') or str(chunk)
                 
                 if isinstance(val, list):
                     val = " ".join(str(v) for v in val)
                 
                 context_parts.append(str(val))
            
            context_text = " ".join(context_parts)
            context_words = set(context_text.lower().split())
            
            # 2. Prepare Response Tokens (removing common stop words)
            stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was", "were"}
            response_words = [w.lower() for w in response.split() if w.isalnum()]
            significant_words = [w for w in response_words if w not in stop_words]
            
            if not significant_words:
                return 0.0
                
            # 3. Calculate Overlap
            matches = sum(1 for w in significant_words if w in context_words)
            score = matches / len(significant_words)
            
            return round(score, 2)
        except Exception as e:
            print(f"Grounding Score Error: {e}")
            return 0.0

    def generate_title(self, query: str) -> str:
        prompt = """Create a short, descriptive title for a chat conversation.
Given the user's first message, generate a title that:
1. Is EXACTLY 2-3 words (no more, no less)
2. Captures the main topic or intent
3. Uses title case (capitalize first letter of each word)
4. Contains NO special characters, emojis, or punctuation
5. Is descriptive and searchable

Rules:
- If the question is about a person, use their name (e.g., "Einstein Biography")
- If it's a how-to, start with the action verb (e.g., "Build Chatbot")
- If it's a comparison, use "vs" (e.g., "Python vs JavaScript")
- For data queries, use the subject (e.g., "Sales Analysis")
- Keep it simple and clear

Examples:
User: "How do I build a RAG chatbot with Redis and ChromaDB?"
Title: "Build RAG Chatbot"

User: "What's the difference between React and Vue?"
Title: "React vs Vue"

User: "Explain quantum computing in simple terms"
Title: "Quantum Computing Explained"

Respond with ONLY the title, nothing else."""

        messages = [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"User message: {query}"}
        ]
        
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=20,
                top_p=1,
                stream=False,
                stop=None,
            )
            title = completion.choices[0].message.content.strip()
            # Clean any potential quotes or punctuation just in case
            title = ''.join(e for e in title if e.isalnum() or e.isspace())
            return title
        except Exception as e:
            print(f"Title generation failed: {e}")
            return "New Chat"

generator = GeneratorService()
