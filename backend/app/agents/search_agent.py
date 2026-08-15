import logging
from app.models.state import ResearchState
from app.mcp.tool_executor import get_tool_executor

logger = logging.getLogger(__name__)

def search_node(state: ResearchState) -> dict:
    logger.info("--- SEARCH AGENT ---")
    executor = get_tool_executor()
    subqueries = state.get("search_queries", [])
    
    all_results = []
    seen_urls = set()
    
    for sq in subqueries:
        logger.info(f"Executing web search for: {sq}")
        try:
            results = executor.execute_tool("search_tool", {"query": sq})
            for res in results:
                url = res.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(res)
        except Exception as e:
            logger.error(f"Search Agent failed for query '{sq}': {str(e)}")
            
    state["search_results"] = all_results
    
    step_msg = f"Search Agent retrieved {len(all_results)} unique web sources."
    logger.info(step_msg)
    
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
