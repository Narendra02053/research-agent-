import logging
import time
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)

class RerankerService:
    """
    Singleton-style initialization for HuggingFace reranker model.
    Optimizes for research-style answers by re-scoring semantic chunks.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RerankerService, cls).__new__(cls)
            cls._instance._model = None
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            logger.info("Initializing HuggingFace Reranker model: BAAI/bge-reranker-base")
            try:
                self._model = CrossEncoder('BAAI/bge-reranker-base', max_length=512, device='cpu')
            except Exception as e:
                logger.error(f"Failed to initialize reranker: {str(e)}")
                self._model = None
        return self._model

    def rerank_results(self, query: str, retrieved_chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Rerank retrieved semantic search results to improve relevance.
        """
        if not retrieved_chunks or not self.model:
            return retrieved_chunks[:top_k]
            
        start_time = time.time()
        logger.info(f"Reranking {len(retrieved_chunks)} chunks for query: '{query}'")

        from app.observability.rag_instrumentation import RerankerSpan
        with RerankerSpan(query=query, input_count=len(retrieved_chunks)) as span:
            try:
                pairs = [[query, chunk.get("content", "")] for chunk in retrieved_chunks]
                scores = self.model.predict(pairs)
                
                for idx, chunk in enumerate(retrieved_chunks):
                    chunk["rerank_score"] = float(scores[idx])
                    
                retrieved_chunks.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)
                
                elapsed = time.time() - start_time
                logger.info(f"Reranking completed in {elapsed:.2f} seconds")
                
                result = retrieved_chunks[:top_k]
                span.finish(top_k_count=len(result))
                return result
            except Exception as e:
                logger.error(f"Reranking failed: {str(e)}")
                result = retrieved_chunks[:top_k]
                span.finish(top_k_count=len(result))
                return result

def get_reranker_service() -> RerankerService:
    return RerankerService()
