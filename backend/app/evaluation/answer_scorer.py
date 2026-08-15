"""
answer_scorer.py
Evaluates the clarity, completeness, and formatting of the generated answer.
"""
import logging

logger = logging.getLogger(__name__)

class AnswerScorer:
    @staticmethod
    def score_answer(report: str, query: str) -> dict:
        """
        Scores the physical attributes of the answer (length, formatting, citations).
        In a production system, this could also use an LLM for nuanced scoring.
        """
        score = 0.5 # base score
        
        # Length check
        if len(report) > 500:
            score += 0.2
            
        # Markdown formatting check
        if "##" in report or "**" in report:
            score += 0.1
            
        # Citation check (very basic heuristic)
        if "http" in report or "Source" in report or "Reference" in report:
            score += 0.2
            
        score = min(score, 1.0)
        
        logger.info(f"Answer scored: {score}")
        return {
            "answer_quality": round(score, 2),
            "length": len(report)
        }
