"""
agentic_research.py  (Step 6 upgrade)
POST /agentic-research
Now returns session_id, timing metrics, and workflow metadata.
Sessions are persisted in Redis memory; history is recorded.
"""

import logging
import asyncio
import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from app.models.state import ResearchState
from app.agents.research_graph import create_research_graph
from app.services.session_service import get_session_service
from app.services.history_service import get_history_service
from app.core.logging_config import async_timed

router = APIRouter(prefix="/agentic-research", tags=["Agentic Research"])
logger = logging.getLogger(__name__)

# Compile LangGraph instance once at import time
research_graph = create_research_graph()


# ------------------------------------------------------------------ #
#  Request / Response Models                                          #
# ------------------------------------------------------------------ #
class AgenticResearchRequest(BaseModel):
    query: str
    session_id: Optional[str] = None   # Pass to continue an existing session


class SourceItem(BaseModel):
    title: str
    url: str


class TimingMetrics(BaseModel):
    total_seconds: float
    graph_seconds: float


class AgenticResearchResponse(BaseModel):
    session_id: str
    query: str
    report: str
    sources: List[SourceItem]
    research_steps: List[str]
    timing: TimingMetrics
    quality_metrics: Dict[str, Any]


# ------------------------------------------------------------------ #
#  Endpoint                                                           #
# ------------------------------------------------------------------ #
@router.post("/", response_model=AgenticResearchResponse)
@async_timed("POST /agentic-research")
async def perform_agentic_research(request: AgenticResearchRequest):
    """
    Full agentic research workflow with session management and observability.
    Flow: Planner -> Search (cached) -> Retrieval (cached) -> Analysis -> Report
    """
    total_start = time.perf_counter()
    session_svc = get_session_service()
    history_svc = get_history_service()
    loop = asyncio.get_running_loop()

    # --- Session lifecycle ---
    if request.session_id:
        session_id = request.session_id
        logger.info(f"Resuming session [id={session_id}]")
    else:
        session_id = session_svc.create_session(request.query)

    session_svc.mark_in_progress(session_id)

    try:
        # --- Build initial LangGraph state ---
        initial_state: ResearchState = {
            "query": request.query,
            "search_queries": [],
            "search_results": [],
            "extracted_content": [],
            "retrieved_chunks": [],
            "reranked_chunks": [],
            "context": "",
            "intermediate_analysis": "",
            "final_answer": "",
            "sources": [],
            "research_steps": [],
            "quality_metrics": {}
        }

        # --- Execute graph in thread executor (nodes are synchronous) ---
        graph_start = time.perf_counter()
        final_state = await loop.run_in_executor(None, research_graph.invoke, initial_state)
        graph_seconds = round(time.perf_counter() - graph_start, 3)

        # --- Timing ---
        total_seconds = round(time.perf_counter() - total_start, 3)
        timing = {"total_seconds": total_seconds, "graph_seconds": graph_seconds}

        # --- Persist completed session ---
        sources = final_state.get("sources", [])
        steps   = final_state.get("research_steps", [])
        report  = final_state.get("final_answer", "")

        session_svc.mark_complete(
            session_id=session_id,
            report=report,
            sources=sources,
            steps=steps,
            timing=timing
        )

        # --- Record in global history ---
        history_svc.record_session(
            session_id=session_id,
            query=request.query,
            report_summary=report[:500],
            sources=sources,
            timing=timing
        )

        # --- Format response ---
        formatted_sources = [SourceItem(title=s["title"], url=s["url"]) for s in sources]

        return AgenticResearchResponse(
            session_id=session_id,
            query=final_state["query"],
            report=report,
            sources=formatted_sources,
            research_steps=steps,
            timing=TimingMetrics(**timing),
            quality_metrics=final_state.get("quality_metrics", {})
        )

    except Exception as e:
        session_svc.mark_failed(session_id, str(e))
        logger.error(f"Agentic research failed [session={session_id}]: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------------ #
#  Session status endpoint                                             #
# ------------------------------------------------------------------ #
@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """
    Retrieve the current status and metadata of a research session.
    Useful for polling / async frontends.
    """
    session_svc = get_session_service()
    session = session_svc.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return session
