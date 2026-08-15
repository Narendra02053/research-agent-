"""
research_quality.py
Aggregates source quality, retrieval quality, grounding quality, and answer quality
into a final confidence score.

PERFORMANCE: hallucination check and answer scoring now run IN PARALLEL
via ThreadPoolExecutor, saving ~25-35s compared to sequential execution.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any

from app.evaluation.source_validator import SourceValidator
from app.evaluation.relevance_evaluator import RelevanceEvaluator
from app.evaluation.hallucination_checker import HallucinationChecker
from app.evaluation.answer_scorer import AnswerScorer

logger = logging.getLogger(__name__)


class ResearchQualityPipeline:
    @staticmethod
    def evaluate_research(state: Dict[str, Any]) -> dict:
        """
        Run the full evaluation pipeline on the current research state.
        LLM-heavy checks (hallucination + answer scoring) run in parallel.
        """
        logger.info("Starting Research Quality Pipeline (parallel LLM checks)...")

        # 1. Source Quality (cheap — no LLM)
        sources = state.get("sources", [])
        source_eval = SourceValidator.evaluate_sources(sources)
        source_quality = source_eval["source_quality"]

        # 2. Retrieval Quality (cheap — heuristic)
        query = state.get("query", "")
        retrieved = state.get("retrieved_chunks", [])
        reranked = state.get("reranked_chunks", [])
        retrieval_eval = RelevanceEvaluator.evaluate_retrieval(query, retrieved, reranked)
        retrieval_quality = retrieval_eval["retrieval_quality"]
        retrieval_precision = retrieval_eval["retrieval_precision"]

        # 3+4. Hallucination check + Answer scoring — PARALLEL LLM calls
        context = state.get("context", "")
        report = state.get("final_answer", "")

        hallucination_eval = {}
        answer_eval = {}

        def _run_hallucination():
            return HallucinationChecker.check_hallucinations(query, context, report)

        def _run_answer_scorer():
            return AnswerScorer.score_answer(report, query, context)

        with ThreadPoolExecutor(max_workers=2) as pool:
            future_hallucination = pool.submit(_run_hallucination)
            future_answer = pool.submit(_run_answer_scorer)

            for future in as_completed([future_hallucination, future_answer]):
                if future is future_hallucination:
                    try:
                        hallucination_eval = future.result()
                    except Exception as e:
                        logger.error(f"Hallucination check failed in parallel executor: {e}")
                        hallucination_eval = {
                            "hallucination_risk": 0.5,
                            "grounding_score": 0.5,
                            "unsupported_claims": [],
                            "supported_claims": [],
                        }
                else:
                    try:
                        answer_eval = future.result()
                    except Exception as e:
                        logger.error(f"Answer scoring failed in parallel executor: {e}")
                        answer_eval = {"answer_quality": 0.5}

        hallucination_risk = hallucination_eval.get("hallucination_risk", 0.5)
        grounding_score = hallucination_eval.get("grounding_score", 0.5)

        # 5. Citation Coverage Score
        supported_claims = hallucination_eval.get("supported_claims", [])
        unsupported_claims = hallucination_eval.get("unsupported_claims", [])
        total_claims = len(supported_claims) + len(unsupported_claims)
        citation_coverage = len(supported_claims) / total_claims if total_claims > 0 else 1.0

        answer_quality = answer_eval.get("answer_quality", 0.5)

        # Aggregate Overall Confidence
        # Grounding Score = 30%, Answer Quality = 20%, Retrieval Quality = 20%
        # Source Quality = 10%, Citation Coverage = 20%
        overall_confidence = (
            (grounding_score * 0.3) +
            (answer_quality * 0.2) +
            (retrieval_quality * 0.2) +
            (source_quality * 0.1) +
            (citation_coverage * 0.2)
        )

        # Penalty for high hallucination risk
        if hallucination_risk > 0.4:
            logger.warning("High hallucination risk detected. Reducing overall confidence.")
            overall_confidence *= 0.7

        overall_confidence = min(max(overall_confidence, 0.0), 1.0)

        return {
            "source_quality": round(source_quality, 2),
            "retrieval_quality": round(retrieval_quality, 2),
            "retrieval_precision": round(retrieval_precision, 2),
            "grounding_score": round(grounding_score, 2),
            "hallucination_risk": round(hallucination_risk, 2),
            "citation_coverage": round(citation_coverage, 2),
            "answer_quality": round(answer_quality, 2),
            "overall_confidence": round(overall_confidence, 2),
            "unsupported_claims": unsupported_claims,
            "supported_claims": supported_claims
        }
