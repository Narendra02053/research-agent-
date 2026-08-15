import logging
import json
from app.models.state import ResearchState
from app.core.llm import get_llm_service
from app.core.config import settings

logger = logging.getLogger(__name__)

def planner_node(state: ResearchState) -> dict:
    logger.info("--- PLANNER AGENT ---")
    llm = get_llm_service()
    query = state["query"]
    
    prompt = f"""You are an expert AI Research Planner.
Break down the query into {settings.MAX_SEARCH_SUBQUERIES} specific search queries for a web search engine.
Return ONLY a valid JSON list of strings, no markdown, no explanation.
Example: ["query 1", "query 2"]

USER QUERY: {query}
"""
    try:
        response = llm.generate_response(prompt, task_type="planning")
        cleaned_response = response.replace("```json", "").replace("```", "").strip()
        search_queries = json.loads(cleaned_response)
        
        if not isinstance(search_queries, list):
            raise ValueError("LLM did not return a list.")
        search_queries = search_queries[: settings.MAX_SEARCH_SUBQUERIES]
    except Exception as e:
        logger.error(f"Planner Agent failed to parse queries: {str(e)}. Defaulting to original query.")
        search_queries = [query]
        
    state["search_queries"] = search_queries
    
    step_msg = f"Planner Agent generated {len(search_queries)} subqueries."
    logger.info(step_msg)
    
    # Initialize research_steps if not present
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
