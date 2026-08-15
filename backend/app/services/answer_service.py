import logging
from typing import List, Dict, Any

from app.rag.vector_store import get_vector_store
from app.rag.reranker import get_reranker_service
from app.services.context_builder import ContextBuilder
from app.core.llm import get_llm_service

logger = logging.getLogger(__name__)

class AnswerService:
    def __init__(self):
        self.vector_store = get_vector_store()
        self.reranker = get_reranker_service()
        self.llm_service = get_llm_service()
        self.context_builder = ContextBuilder()

    def generate_research_answer(self, query: str) -> Dict[str, Any]:
        """
        Semantic retrieval -> reranking -> context building -> grounded LLM generation.
        """
        try:
            # 1. Semantic retrieval from Qdrant
            retrieved_chunks = self.vector_store.search_similar_content(query, limit=10)
            if not retrieved_chunks:
                logger.warning(f"No chunks retrieved for query: '{query}'")
                return {
                    "answer": "I could not find relevant information to answer your query.",
                    "sources": []
                }
                
            # 2. Reranking
            reranked_chunks = self.reranker.rerank_results(query, retrieved_chunks, top_k=5)
            
            # 3. Context building
            context = self.context_builder.build_research_context(query, reranked_chunks)
            
            # 4. Citation-aware prompt engineering
            prompt = (
                "You are an expert AI Research Assistant. Your task is to provide a comprehensive, "
                "well-structured, and factual answer to the user's query.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "- Use ONLY the retrieved context provided below.\n"
                "- Do NOT fabricate information (no hallucinations).\n"
                "- Cite your sources inline using the exact [Source X] format provided in the context.\n"
                "- Provide structured analysis and explain your reasoning clearly.\n\n"
                f"USER QUERY: {query}\n\n"
                f"RETRIEVED CONTEXT:\n{context}\n\n"
                "ANSWER:"
            )
            
            # 5. LLM Answer Generation
            answer = self.llm_service.generate_response(prompt)
            
            # 6. Extract unique sources for the response payload
            sources = []
            seen_urls = set()
            for chunk in reranked_chunks:
                url = chunk["metadata"].get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    sources.append({
                        "title": chunk["metadata"].get("title", "Unknown Title"),
                        "url": url
                    })
                    
            return {
                "answer": answer,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Error during research answer generation: {str(e)}")
            raise e
