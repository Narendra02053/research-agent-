# search_agent.py - Agent for performing web searches.
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.state import ResearchState
from app.mcp.tool_executor import get_tool_executor

logger = logging.getLogger(__name__)


def _search_one(executor, sq: str) -> list:
    """Run a single Tavily search and return results list."""
    try:
        logger.info(f"Executing web search for: {sq}")
        return executor.execute_tool("search_tool", {"query": sq})
    except Exception as e:
        logger.error(f"Search Agent failed for query '{sq}': {str(e)}")
        return []


def search_node(state: ResearchState) -> dict:
    logger.info("--- SEARCH AGENT ---")
    executor = get_tool_executor()
    subqueries = state.get("search_queries", [])

    all_results = []
    seen_urls: set = set()

    # Run all sub-queries concurrently instead of sequentially
    max_workers = min(len(subqueries), 4) if subqueries else 1
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_search_one, executor, sq): sq for sq in subqueries}
        for future in as_completed(futures):
            for res in future.result():
                url = res.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(res)

    state["search_results"] = all_results

    step_msg = f"Search Agent retrieved {len(all_results)} unique web sources."
    logger.info(step_msg)

    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps

    return state
