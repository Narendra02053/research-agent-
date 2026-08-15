import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ContextBuilder:
    @staticmethod
    def build_research_context(query: str, reranked_chunks: List[Dict[str, Any]]) -> str:
        """
        Structure context professionally for the LLM.
        Removes noisy content, avoids token waste, and preserves source attribution.
        """
        logger.info("Building structured research context...")
        
        context_parts = []
        seen_content = set()
        
        for idx, chunk in enumerate(reranked_chunks):
            title = chunk["metadata"].get("title", "Unknown Title")
            url = chunk["metadata"].get("url", "Unknown URL")
            content = chunk.get("content", "").strip()
            
            # Compress noisy content and remove exact duplicates to avoid token waste
            if not content or content in seen_content:
                continue
                
            seen_content.add(content)
            
            context_block = (
                f"[Source {idx + 1}]\n"
                f"Title: {title}\n"
                f"URL: {url}\n"
                f"Key Information:\n{content}\n"
            )
            context_parts.append(context_block)
            
        final_context = "\n".join(context_parts)
        logger.info(f"Context building completed with {len(context_parts)} sources.")
        return final_context
