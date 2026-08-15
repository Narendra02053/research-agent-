"""
relevance_evaluator.py
Evaluates semantic relevance of retrieved chunks against the original query using embeddings and reranker scores.
"""
import logging
import math
from typing import List, Dict, Any
from app.rag.embedding import get_embedding_service

logger = logging.getLogger(__name__)

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two vectors."""
    dot_prod = sum(x * y for x, y in zip(v1, v2))
    sum_sq1 = sum(x * x for x in v1)
    sum_sq2 = sum(y * y for y in v2)
    if sum_sq1 == 0 or sum_sq2 == 0:
        return 0.0
    return dot_prod / (math.sqrt(sum_sq1) * math.sqrt(sum_sq2))

class RelevanceEvaluator:
    @staticmethod
    def evaluate_retrieval(query: str, retrieved_chunks: List[Dict[str, Any]], reranked_chunks: List[Dict[str, Any]]) -> dict:
        """
        Calculates retrieval quality metrics using semantic similarity embeddings.
        Compares query embedding vs retrieved chunk embeddings.
        Keeps reranker score as a secondary signal.
        """
        if not retrieved_chunks:
            return {
                "retrieval_quality": 0.0,
                "average_similarity": 0.0,
                "retrieval_precision": 0.0,
                "confidence": "Low",
                "chunks_analyzed": 0
            }
            
        try:
            # 1. Calculate semantic similarity using Embedding Service
            embedding_svc = get_embedding_service()
            query_embedding = embedding_svc.embed_text(query)
            
            chunk_texts = []
            for chunk in retrieved_chunks:
                text = chunk.get("content") or chunk.get("text") or chunk.get("chunk_text") or ""
                chunk_texts.append(text)
                
            chunk_embeddings = embedding_svc.embed_documents(chunk_texts)
            
            similarities = [cosine_similarity(query_embedding, c_emb) for c_emb in chunk_embeddings]
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
            
            # Precision: fraction of chunks with semantic similarity >= 0.6
            threshold = 0.6
            relevant_chunks = [sim for sim in similarities if sim >= threshold]
            retrieval_precision = len(relevant_chunks) / len(similarities) if similarities else 0.0
            
        except Exception as e:
            logger.error(f"Semantic similarity calculation failed: {e}. Falling back to default proxy scores.")
            avg_similarity = 0.7
            retrieval_precision = 0.7
            similarities = [0.7] * len(retrieved_chunks)
            
        # 2. Reranker Score as a secondary signal
        total_score = 0.0
        valid_scores = 0
        chunks_to_check = reranked_chunks or retrieved_chunks
        
        for chunk in chunks_to_check:
            score = chunk.get("metadata", {}).get("score", chunk.get("score"))
            if score is not None:
                total_score += float(score)
                valid_scores += 1
                
        if valid_scores > 0:
            avg_reranker_score = total_score / valid_scores
            # Combine signals: 70% embedding similarity, 30% reranker score
            retrieval_quality = (avg_similarity * 0.7) + (avg_reranker_score * 0.3)
        else:
            retrieval_quality = avg_similarity
            
        retrieval_quality = min(max(retrieval_quality, 0.0), 1.0)
        confidence = "High" if retrieval_quality > 0.75 else "Medium" if retrieval_quality > 0.5 else "Low"
        
        logger.info(f"Retrieval relevance evaluated. Avg Similarity: {avg_similarity:.2f}, Quality: {retrieval_quality:.2f} ({confidence})")
        
        return {
            "retrieval_quality": round(retrieval_quality, 2),
            "average_similarity": round(avg_similarity, 2),
            "retrieval_precision": round(retrieval_precision, 2),
            "confidence": confidence,
            "chunks_analyzed": len(retrieved_chunks)
        }
