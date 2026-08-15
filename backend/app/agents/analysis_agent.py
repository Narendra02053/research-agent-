"""
analysis_agent.py
OPTIMIZED: Merged Analysis + Report into ONE LLM call.
Previously: analysis LLM call (~25s) + report LLM call (~25s) = ~50s sequential.
Now:        single combined call (~25s) — saves ~25s per query.
The intermediate_analysis field is set to a brief summary for backward compat.
"""
import logging
from app.models.state import ResearchState
from app.core.llm import get_llm_service
from app.core.config import settings

logger = logging.getLogger(__name__)


def analysis_node(state: ResearchState) -> dict:
    logger.info("--- ANALYSIS + REPORT AGENT (merged, 1 LLM call) ---")
    llm = get_llm_service()

    query = state["query"]
    context = state.get("context", "")
    sources = state.get("sources", [])

    if not context.strip():
        logger.warning("No context available for Analysis+Report Agent.")
        state["intermediate_analysis"] = "No context found."
        state["final_answer"] = "No relevant information was found for this query."
        steps = state.get("research_steps", [])
        steps.append("Analysis skipped — no context retrieved.")
        state["research_steps"] = steps
        return state

    # Trim context to avoid large token payloads (faster LLM inference)
    if len(context) > settings.MAX_CONTEXT_CHARS:
        context = context[: settings.MAX_CONTEXT_CHARS] + "\n\n[context truncated]"
        logger.info(f"Context trimmed to {settings.MAX_CONTEXT_CHARS} chars.")

    sources_text = "\n".join([f"- {s.get('title','Untitled')}: {s.get('url','')}" for s in sources])

    prompt = f"""You are an expert AI Research Analyst and Report Writer.
Given the source context and user query, perform the following in ONE response:

1. Briefly analyze key facts and patterns from the context (2-3 sentences internally).
2. Immediately produce a final, professional research report in Markdown.

REQUIREMENTS FOR THE REPORT:
- Use clear sections with ## headers.
- Be concise but highly informative (aim for 400-600 words).
- Cite sources inline like [Source Title](url).
- Avoid repeating yourself.
- Do NOT include preamble like "Here is the report:" — go straight to the Markdown.

USER QUERY: {query}

SOURCE CONTEXT:
{context}

SOURCES:
{sources_text}

FINAL REPORT:
"""

    try:
        report = llm.generate_response(prompt, task_type="deep_analysis")
    except Exception as e:
        logger.error(f"Analysis+Report Agent failed: {e}")
        report = f"Research failed to generate a report. Error: {e}"

    # Store both fields so downstream nodes stay compatible
    state["intermediate_analysis"] = report[:500] + "..." if len(report) > 500 else report
    state["final_answer"] = report

    step_msg = "Analysis+Report Agent synthesized findings and generated the final report in one pass."
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps

    return state
