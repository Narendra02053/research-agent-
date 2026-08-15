import logging
import trafilatura
from app.core.cache import get_cache
from app.core.logging_config import timed

logger = logging.getLogger(__name__)

class ExtractionService:
    def __init__(self):
        self.cache = get_cache()

    @timed("Webpage extraction")
    def extract_webpage_content(self, url: str) -> str:
        """
        Download and extract clean readable text from a URL using Trafilatura.
        Results are cached in Redis for 2 hours to avoid re-fetching.
        Returns empty string on failure.
        """
        # --- Cache check ---
        cached = self.cache.get_webpage_content(url)
        if cached:
            return cached["content"]

        try:
            downloaded = trafilatura.fetch_url(url)
            if not downloaded:
                logger.warning(f"Failed to download content from URL: {url}")
                return ""

            clean_text = trafilatura.extract(downloaded)
            if not clean_text:
                logger.warning(f"Trafilatura returned empty text from URL: {url}")
                return ""

            # --- Cache store ---
            self.cache.set_webpage_content(url, clean_text, ttl=7200)
            return clean_text

        except Exception as e:
            logger.error(f"Error extracting content from URL '{url}': {str(e)}")
            return ""


def get_extraction_service() -> ExtractionService:
    return ExtractionService()
