import logging
from app.models.state import ResearchState
from app.evaluation.research_quality import ResearchQualityPipeline

logger = logging.getLogger(__name__)

def evaluation_node(state: ResearchState) -> dict:
    logger.info("--- EVALUATION AGENT ---")
    
    # Run the quality pipeline
    metrics = ResearchQualityPipeline.evaluate_research(state)
    state["quality_metrics"] = metrics
    
    # Log findings
    logger.info(f"Research evaluation complete. Overall Confidence: {metrics['overall_confidence']}")
    if metrics["hallucination_risk"] > 0.4:
        logger.warning(f"High hallucination risk! Unsupported claims: {metrics['unsupported_claims']}")
        
    step_msg = f"Evaluation Agent validated output. Confidence: {metrics['overall_confidence']*100:.0f}%"
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
