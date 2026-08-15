import logging
from app.models.state import ResearchState
from app.core.llm import get_llm_service

logger = logging.getLogger(__name__)

def analysis_node(state: ResearchState) -> dict:
    logger.info("--- ANALYSIS AGENT ---")
    llm = get_llm_service()
    
    query = state["query"]
    context = state.get("context", "")
    
    if not context.strip():
        logger.warning("No context available for Analysis Agent.")
        state["intermediate_analysis"] = "No context was found to analyze."
        return state
        
    prompt = f"""
You are an expert AI Research Analyst.
Analyze the provided context against the user query. Identify key patterns, facts, and insights.
Synthesize the findings into a structured intermediate reasoning draft.
Ensure your analysis is heavily grounded in the provided context and avoids hallucinations.

USER QUERY: {query}

CONTEXT:
{context}

ANALYSIS DRAFT:
"""
    try:
        analysis = llm.generate_response(prompt)
    except Exception as e:
        logger.error(f"Analysis Agent failed: {str(e)}")
        analysis = "Analysis failed to generate."
        
    state["intermediate_analysis"] = analysis
    
    step_msg = "Analysis Agent synthesized findings and prepared structured reasoning."
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
