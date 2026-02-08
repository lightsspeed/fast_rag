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
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Generate 3 different search queries based on the user's question to help find more relevant information in a document database. Return only the queries, one per line, without numbers or bullets."},
            {"role": "user", "content": query}
        ]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
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
        context_text = "\n\n".join(
            [f"[Chunk {i+1}]\n{chunk['text']}" for i, chunk in enumerate(context_chunks)]
        )
        
        query_type = self._classify_query_type(query)
        
        # Adjust instructions based on query type
        style_guidance = {
            'howto': "Focus on step-by-step instructions and practical examples. Include prerequisites if mentioned in context.",
            'comparison': "Present both sides clearly. Use a balanced structure highlighting key differences.",
            'explanation': "Provide a clear conceptual overview first, then dive into details.",
            'troubleshooting': "Start with the most likely solution. Provide debugging steps if available.",
            'general': "Answer directly and comprehensively."
        }
        
        system_instructions = f"""You are a highly capable AI specialized in technical troubleshooting and document analysis. Your goal is to provide a comprehensive, in-depth explanation based on the provided context.

**Technical Guidelines:**
1. **Depth & Detail**: Provide extensive, step-by-step technical explanations. Never be brief if the context provides details.
2. **NO INLINE CITATIONS**: Do not use citations like "[Chunk 1]" or "[1]" in your response. The citations are handled by the UI "Sources" tab; your text should be clean and professional.
3. **Answer directly**: Address the user's specific problem (e.g., error codes, BSOD symptoms) using technical steps from the documentation.
4. **Formatting**: Use headers, bold text, and code blocks to make complex instructions easy to follow.

**Context Provided:**
{context_text}

Remember: Be thorough, technical, and natural. Focus on solving the user's problem completely."""
        
        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": query}
        ]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,  # Slightly higher for more natural language
            max_tokens=2048,
            top_p=0.95,  # Slightly higher for better fluency
            stream=True,
            stop=None,
        )

        for chunk in completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

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
