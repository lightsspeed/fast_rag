import httpx
from typing import List, Dict, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class BraveSearchService:
    def __init__(self):
        self.api_key = settings.BRAVE_API_KEY
        self.base_url = "https://api.search.brave.com/res/v1/web/search"

    async def search(self, query: str, count: int = 5) -> List[Dict]:
        if not self.api_key:
            logger.warning("BRAVE_API_KEY is not set. Skipping web search.")
            return []

        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self.api_key
        }
        params = {
            "q": query,
            "count": count
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.base_url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "id": f"web_{item.get('url')}",
                        "text": item.get("description", ""),
                        "metadata": {
                            "source": item.get("url"),
                            "title": item.get("title"),
                            "is_web": True
                        },
                        "score": 0.85 # Assume high relevance if Brave returns it for now, or use reranker
                    })
                return results
        except Exception as e:
            logger.error(f"Brave search failed: {e}")
            return []

web_search = BraveSearchService()
