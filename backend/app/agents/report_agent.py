import logging
from app.models.state import ResearchState
from app.mcp.tool_executor import get_tool_executor

logger = logging.getLogger(__name__)

def report_node(state: ResearchState) -> dict:
    logger.info("--- REPORT AGENT ---")
    executor = get_tool_executor()
    
    query = state["query"]
    analysis = state.get("intermediate_analysis", "")
    sources = state.get("sources", [])
    
    try:
        report = executor.execute_tool("report_tool", {
            "query": query,
            "analysis": analysis,
            "sources": sources
        })
    except Exception as e:
        logger.error(f"Report Agent failed: {str(e)}")
        report = "Failed to generate the final report."
        
    state["final_answer"] = report
    
    step_msg = "Report Agent generated the final professional research report."
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
