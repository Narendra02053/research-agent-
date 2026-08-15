"""
hallucination_checker.py
Verifies generated answers against retrieved context to detect unsupported claims.
"""
import logging
import json
from app.core.llm import get_llm_service

logger = logging.getLogger(__name__)

class HallucinationChecker:
    @staticmethod
    def check_hallucinations(query: str, context: str, report: str) -> dict:
        """
        Uses an LLM to check if the report hallucinates facts not present in the context.
        """
        llm = get_llm_service()
        
        prompt = f"""
You are an expert Fact-Checker and Hallucination Detector.
Your task is to compare a generated Research Report against the provided Source Context.
Detect any claims made in the Report that are NOT supported by the Context.

USER QUERY: {query}

SOURCE CONTEXT:
{context}

GENERATED REPORT:
{report}

INSTRUCTIONS:
Calculate a 'hallucination_risk' score between 0.0 (no hallucinations, fully grounded) and 1.0 (completely hallucinated).
List any 'unsupported_claims'.
Return ONLY valid JSON.

Format:
{{
    "hallucination_risk": 0.15,
    "unsupported_claims": ["claim 1", "claim 2"]
}}
"""
        try:
            response = llm.generate_response(prompt, task_type="hallucination")
            cleaned = response.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            
            risk = float(result.get("hallucination_risk", 0.5))
            claims = result.get("unsupported_claims", [])
            
            grounding_confidence = 1.0 - risk
            logger.info(f"Hallucination check complete. Risk: {risk}, Grounding: {grounding_confidence}")
            
            return {
                "hallucination_risk": round(risk, 2),
                "grounding_score": round(grounding_confidence, 2),
                "unsupported_claims": claims
            }
        except Exception as e:
            logger.error(f"Hallucination check failed: {e}")
            return {
                "hallucination_risk": 0.5,
                "grounding_score": 0.5,
                "unsupported_claims": ["Check failed to execute."]
            }
