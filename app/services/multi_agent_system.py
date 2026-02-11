from groq import Groq
from app.core.config import settings
from app.core.rate_limiter import groq_rate_limiter
from typing import List, Dict, Any, AsyncGenerator
import logging

logger = logging.getLogger(__name__)

class MultiAgentSystem:
    """Coordinates specialized agents for deep research, analysis, and writing."""
    
    def __init__(self):
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = "llama-3.3-70b-versatile"

    async def execute_task_stream(self, query: str, context: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """Kicks off the agent workflow and streams the final answer."""
        logger.info("Multi-Agent System activated (Streaming).")
        
        # 1. Researcher Agent: Gathers more detail
        research_notes = await self._researcher_agent(query, context)
        
        # 2. Analyst Agent: Processes technical/data details
        analysis = await self._analyst_agent(query, research_notes)
        
        # 3. Writer Agent: Final synthesis (Streaming)
        async for token in self._writer_agent_stream(query, analysis):
            yield token

    async def _researcher_agent(self, query: str, context: List[Dict[str, Any]]) -> str:
        prompt = f"Role: Researcher Agent. Task: Analyze the context and query. Find missing gaps or provide deeper insights. Query: {query} Context: {context}"
        return await self._call_llm(prompt)

    async def _analyst_agent(self, query: str, research_notes: str) -> str:
        prompt = f"Role: Analyst Agent. Task: Analyze the technical details, logic, or data provided by the researcher. Ensure accuracy. Query: {query} Notes: {research_notes}"
        return await self._call_llm(prompt)

    async def _writer_agent_stream(self, query: str, analysis: str) -> AsyncGenerator[str, None]:
        prompt = f"Role: Writer Agent. Task: Synthesize all information into a beautiful, production-grade response for the user. Query: {query} Analysis: {analysis}"
        async for token in self._call_llm_stream(prompt):
            yield token

    async def _call_llm(self, prompt: str) -> str:
        groq_rate_limiter.wait_if_needed()
        completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.3
        )
        return completion.choices[0].message.content

    async def _call_llm_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        groq_rate_limiter.wait_if_needed()
        completion = self.client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=self.model,
            temperature=0.3,
            stream=True
        )
        for chunk in completion:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

multi_agent_system = MultiAgentSystem()
