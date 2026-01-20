from groq import Groq
from app.core.config import settings
from typing import List, AsyncGenerator

class GeneratorService:
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        
        self.system_prompt_template = """You are a helpful AI assistant that answers questions based on the provided context.

Guidelines:
1. Answer using information from the context below.
2. If the context doesn't contain enough information, say so clearly.
3. Cite the source chunk number when making specific claims.
4. Be as detailed as possible based on the provided context. If the user asks for "full info", provide a comprehensive explanation.
5. If multiple chunks contradict, acknowledge this and present both perspectives.

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

    async def generate_stream(self, query: str, context_chunks: List[dict]) -> AsyncGenerator[str, None]:
        # Prepare context string
        context_text = "\n\n".join(
            [f"Chunk {i+1}: {chunk['text']}" for i, chunk in enumerate(context_chunks)]
        )
        
        # Better structure for Groq/Llama
        system_instructions = f"""You are a helpful AI assistant that answers questions based on the provided context.
Provide detailed, well-structured answers in markdown format.
Note: Some chunks contains tables marked with [Table Start] and [Table End].
Interpret these as structured data and present them clearly in your answers if relevant.

CRITICAL RULE: Start EVERY response with a title on the first line in this exact format:
**Title: [2-3 Word Title]**

This title will be used to name the chat conversation. It must follow these rules:
1. Is EXACTLY 2-3 words (no more, no less)
2. Captures the main topic or intent
3. Uses Title Case
4. Contains NO special characters, emojis, or punctuation (except the bold markers)
5. Descriptive and searchable

Example Guidance:
- How-to: Action verb (e.g., "Build Chatbot")
- Comparison: Use "vs" (e.g., "React vs Vue")
- Data: Subject (e.g., "Sales Analysis")
- Person: Name (e.g., "Einstein Biography")
- Keep it simple and clear.

After the Title line, proceed with your actual answer."""
        
        messages = [
            {"role": "system", "content": system_instructions},
            {"role": "user", "content": f"Context:\n{context_text}\n\nUser Question: {query}"}
        ]

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            top_p=0.9,
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
