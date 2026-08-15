import os
import logging
from typing import List, Dict

from tavily import TavilyClient
from app.core.cache import get_cache
from app.core.logging_config import timed

logger = logging.getLogger(__name__)

class SearchService:
    def __init__(self):
        """
        Initialize SearchService with Tavily client and Redis cache.
        """
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key or api_key == "your_api_key_here":
            logger.warning("TAVILY_API_KEY is not set or using the default example value.")
        try:
            self.client = TavilyClient(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize TavilyClient: {str(e)}")
            self.client = None
        self.cache = get_cache()

    @timed("Tavily web search")
    def search_web(self, query: str) -> List[Dict[str, str]]:
        """
        Search the internet using Tavily with Redis cache layer.
        Returns top 5 relevant results with title, url, content_snippet.
        Cache TTL: 1 hour.
        """
        if not self.client:
            raise RuntimeError("Tavily client is not properly initialized. Check your API key.")

        # --- Cache check ---
        cached = self.cache.get_search_results(query)
        if cached:
            return cached["results"]

        try:
            response = self.client.search(query=query, max_results=5)
            results = []
            for result in response.get("results", []):
                results.append({
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "content_snippet": result.get("content", "")
                })

            # --- Cache store ---
            self.cache.set_search_results(query, results, ttl=3600)
            return results

        except Exception as e:
            logger.error(f"Error during Tavily search for query '{query}': {str(e)}")
            raise e


def get_search_service() -> SearchService:
    return SearchService()
