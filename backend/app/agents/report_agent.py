# report_agent.py - Agent for compiling and generating research reports.
"""
report_agent.py
Optimized: This node is now a no-op because report generation is done in the merged analysis node.
This avoids an extra redundant LLM call.
"""
import logging
from app.models.state import ResearchState

logger = logging.getLogger(__name__)

def report_node(state: ResearchState) -> dict:
    logger.info("--- REPORT AGENT (noop) ---")
    # Report was already generated in the analysis node, so we just pass through.
    step_msg = "Report Agent passed through (optimized merged execution)."
    steps = state.get("research_steps", [])
    if step_msg not in steps:
        steps.append(step_msg)
    state["research_steps"] = steps
    return state
