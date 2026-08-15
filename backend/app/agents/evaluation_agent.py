# evaluation_agent.py - Agent for evaluating research findings.
"""
evaluation_agent.py
Runs hallucination check and answer scoring in PARALLEL using ThreadPoolExecutor.
Previously these two LLM calls ran sequentially (~30s each = 60s wasted).
Now they run concurrently, saving ~30s total.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.state import ResearchState
from app.evaluation.research_quality import ResearchQualityPipeline

logger = logging.getLogger(__name__)


def evaluation_node(state: ResearchState) -> dict:
    logger.info("--- EVALUATION AGENT (parallel) ---")

    # Run the quality pipeline — internally now uses parallel LLM calls
    metrics = ResearchQualityPipeline.evaluate_research(state)
    state["quality_metrics"] = metrics

    confidence_pct = metrics["overall_confidence"] * 100
    logger.info(f"Evaluation complete. Confidence: {confidence_pct:.0f}%  "
                f"Hallucination risk: {metrics['hallucination_risk']:.2f}")

    if metrics["hallucination_risk"] > 0.4:
        logger.warning(
            f"High hallucination risk! "
            f"Unsupported claims: {metrics['unsupported_claims']}"
        )

    step_msg = (
        f"Evaluation Agent validated output. "
        f"Confidence: {confidence_pct:.0f}%  "
        f"Grounding: {metrics['grounding_score']*100:.0f}%"
    )
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps

    return state
