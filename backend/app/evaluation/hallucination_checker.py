"""
hallucination_checker.py
Verifies generated answers against retrieved context to detect unsupported and supported claims.
"""
import logging
from pydantic import BaseModel, Field
from typing import List
from app.core.llm import get_llm_service
from app.utils.json_parser import parse_and_validate_json

logger = logging.getLogger(__name__)

class HallucinationReport(BaseModel):
    hallucination_risk: float = Field(..., ge=0.0, le=1.0)
    grounding_score: float = Field(..., ge=0.0, le=1.0)
    unsupported_claims: List[str] = Field(default_factory=list)
    supported_claims: List[str] = Field(default_factory=list)

class HallucinationChecker:
    @staticmethod
    def check_hallucinations(query: str, context: str, report: str) -> dict:
        """
        Uses an LLM to check if the report hallucinates facts not present in the context.
        Returns risk, grounding score, unsupported claims, and supported claims.
        """
        llm = get_llm_service()
        
        prompt = f"""
You are an expert Fact-Checker and Hallucination Detector.
Your task is to compare a generated Research Report against the provided Source Context.
Identify specific claims made in the Report and determine if they are supported by the Context.

USER QUERY: {query}

SOURCE CONTEXT:
{context}

GENERATED REPORT:
{report}

INSTRUCTIONS:
1. Extract the key factual claims made in the GENERATED REPORT.
2. For each claim, check if it is directly or indirectly supported by the SOURCE CONTEXT.
3. List the supported claims in "supported_claims".
4. List the unsupported claims (claims not present or contradicted in the context) in "unsupported_claims".
5. Calculate "hallucination_risk" between 0.0 (fully grounded) and 1.0 (completely hallucinated).
6. Calculate "grounding_score" as 1.0 - "hallucination_risk".
7. Return ONLY valid JSON matching this schema:
{{
  "hallucination_risk": float,
  "grounding_score": float,
  "unsupported_claims": [str],
  "supported_claims": [str]
}}
"""
        try:
            response = llm.generate_response(prompt, task_type="hallucination")
            report_data = parse_and_validate_json(response, HallucinationReport)
            
            logger.info(f"Hallucination check complete. Risk: {report_data.hallucination_risk}, Grounding: {report_data.grounding_score}")
            return report_data.model_dump()
            
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}. Returning fallback values.")
            return {
                "hallucination_risk": 0.5,
                "grounding_score": 0.5,
                "unsupported_claims": ["Check failed to execute or parse."],
                "supported_claims": []
            }
