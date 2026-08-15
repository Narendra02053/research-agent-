"""
answer_scorer.py
Evaluates the clarity, completeness, and formatting of the generated answer using an LLM.
"""
import logging
from pydantic import BaseModel, Field
from app.core.llm import get_llm_service
from app.utils.json_parser import parse_and_validate_json

logger = logging.getLogger(__name__)

class AnswerScorerResult(BaseModel):
    completeness: float = Field(..., ge=0.0, le=1.0)
    accuracy: float = Field(..., ge=0.0, le=1.0)
    clarity: float = Field(..., ge=0.0, le=1.0)
    evidence_usage: float = Field(..., ge=0.0, le=1.0)
    citation_quality: float = Field(..., ge=0.0, le=1.0)
    answer_quality: float = Field(..., ge=0.0, le=1.0)

class AnswerScorer:
    @staticmethod
    def score_answer(report: str, query: str, context: str = "") -> dict:
        """
        Scores the quality of the answer using an LLM across multiple dimensions:
        Completeness, Accuracy, Clarity, Evidence Usage, Query Coverage, and Citation Quality.
        """
        llm = get_llm_service()
        
        prompt = f"""
You are an expert evaluator of scientific and technical research reports.
Your task is to evaluate a generated Research Report against the User Query and optionally the Source Context.

USER QUERY:
{query}

SOURCE CONTEXT:
{context}

GENERATED REPORT:
{report}

INSTRUCTIONS:
Evaluate the report across the following criteria. Assign a score between 0.0 (very poor) and 1.0 (excellent) for each:
1. "completeness": Does the report address all aspects of the query and provide a thorough answer?
2. "accuracy": Are the facts and details presented in the report correct and aligned with the provided context?
3. "clarity": Is the report well-structured, easy to read, and free of grammatical or stylistic issues?
4. "evidence_usage": Does the report effectively use evidence/facts to support its assertions?
5. "citation_quality": Are the citations and references used appropriately, correctly placed, and credible?
6. "answer_quality": Provide an overall quality score for the answer based on all criteria.

Return ONLY a valid JSON object with the following schema:
{{
  "completeness": float,
  "accuracy": float,
  "clarity": float,
  "evidence_usage": float,
  "citation_quality": float,
  "answer_quality": float
}}
"""
        try:
            response = llm.generate_response(prompt, task_type="evaluation")
            result = parse_and_validate_json(response, AnswerScorerResult)
            
            logger.info(f"Answer LLM scoring complete. Quality: {result.answer_quality}")
            return result.model_dump()
            
        except Exception as e:
            logger.error(f"LLM Answer scoring failed: {e}. Falling back to default scoring.")
            # Fallback simple scoring
            score = 0.5
            if len(report) > 500:
                score += 0.2
            if "##" in report or "**" in report:
                score += 0.1
            if "http" in report or "Source" in report or "Reference" in report:
                score += 0.2
            score = min(score, 1.0)
            
            return {
                "completeness": round(score, 2),
                "accuracy": round(score, 2),
                "clarity": round(score, 2),
                "evidence_usage": round(score, 2),
                "citation_quality": round(score, 2),
                "answer_quality": round(score, 2)
            }
