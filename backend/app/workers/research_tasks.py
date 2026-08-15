"""
research_tasks.py
Celery tasks that execute the full LangGraph research workflow in the background.
Includes progress tracking, retry logic, and result persistence.
"""

import time
import logging
from app.workers.celery_app import celery_app
from app.services.job_service import get_job_service
from app.services.history_service import get_history_service
from app.models.state import ResearchState

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="research.run_deep_research",
    max_retries=2,
    default_retry_delay=10,
    acks_late=True
)
def run_deep_research_task(self, job_id: str, query: str):
    """
    Background Celery task that executes the full agentic research pipeline.
    Updates job progress in Redis at each major stage.
    """
    job_svc = get_job_service()
    history_svc = get_history_service()
    total_start = time.perf_counter()

    try:
        from app.mcp import init_mcp
        init_mcp()

        # ---- Mark running ------------------------------------------------
        job_svc.mark_running(job_id, step="initializing", progress=5)

        # Check for early cancellation
        job = job_svc.get_job(job_id)
        if job and job.get("status") == "cancelled":
            logger.info(f"Job {job_id} was cancelled before execution.")
            return

        # ---- Import and build graph (lazy to avoid heavy imports at worker boot)
        from app.agents.research_graph import create_research_graph
        research_graph = create_research_graph()

        # ---- Initialise state -------------------------------------------
        initial_state: ResearchState = {
            "query": query,
            "job_id": job_id,
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

        # ---- Execute graph with per-node progress -------------------------
        step_progress = {
            "planner": 15,
            "search": 35,
            "retrieval": 55,
            "analysis": 75,
            "report": 90,
            "evaluation": 98,
        }

        graph_start = time.perf_counter()
        final_state = dict(initial_state)
        for event in research_graph.stream(initial_state):
            for node_name, node_output in event.items():
                if isinstance(node_output, dict):
                    final_state.update(node_output)
                progress = step_progress.get(node_name, 50)
                job_svc.update_progress(job_id, node_name, progress)
        graph_seconds = round(time.perf_counter() - graph_start, 3)

        # ---- Collect results --------------------------------------------
        total_seconds = round(time.perf_counter() - total_start, 3)
        timing = {"total_seconds": total_seconds, "graph_seconds": graph_seconds}

        report = final_state.get("final_answer", "")
        sources = final_state.get("sources", [])
        steps = final_state.get("research_steps", [])
        quality = final_state.get("quality_metrics", {})

        # ---- Persist completed job --------------------------------------
        job_svc.mark_complete(
            job_id=job_id,
            report=report,
            sources=sources,
            quality_metrics=quality,
            steps=steps,
            timing=timing
        )

        # ---- Record to global history -----------------------------------
        history_svc.record_session(
            session_id=job_id,
            query=query,
            report_summary=report[:500],
            sources=sources,
            timing=timing
        )

        logger.info(f"Background research completed [job={job_id}] in {total_seconds}s")

    except Exception as exc:
        logger.error(f"Background research failed [job={job_id}]: {exc}")
        job_svc.mark_failed(job_id, str(exc), step="graph_execution")

        # Only retry transient/network failures — not logic or config errors
        retryable = isinstance(exc, (ConnectionError, TimeoutError, OSError))
        if retryable:
            try:
                raise self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                job_svc.mark_failed(job_id, f"Max retries exceeded: {exc}", step="final_failure")
                logger.error(f"Job {job_id} exhausted all retries.")
