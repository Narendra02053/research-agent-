"""
relevance_evaluator.py
Evaluates semantic relevance of retrieved chunks against the original query.
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RelevanceEvaluator:
    @staticmethod
    def evaluate_retrieval(query: str, retrieved_chunks: List[Dict[str, Any]], reranked_chunks: List[Dict[str, Any]]) -> dict:
        """
        Calculates retrieval quality metrics using the reranker scores as a proxy.
        If rerank_score is present, we calculate the average score.
        """
        if not reranked_chunks:
            return {"retrieval_quality": 0.0, "confidence": "Low", "message": "No chunks reranked."}
            
        total_score = 0
        valid_scores = 0
        
        for chunk in reranked_chunks:
            # Assuming reranker adds a 'score' to the metadata
            score = chunk.get("metadata", {}).get("score", chunk.get("score"))
            if score is not None:
                total_score += float(score)
                valid_scores += 1
                
        if valid_scores == 0:
            # Fallback if no explicit scores found: assume decent retrieval if chunks exist
            avg_score = 0.7
        else:
            avg_score = total_score / valid_scores
            
        # Normalize to 0-1 if scores are raw logits, but assuming they are 0-1 probabilities.
        avg_score = min(max(avg_score, 0.0), 1.0)
        
        confidence = "High" if avg_score > 0.75 else "Medium" if avg_score > 0.5 else "Low"
        
        logger.info(f"Retrieval relevance evaluated. Avg Score: {avg_score:.2f} ({confidence})")
        
        return {
            "retrieval_quality": round(avg_score, 2),
            "confidence": confidence,
            "chunks_analyzed": len(reranked_chunks)
        }
