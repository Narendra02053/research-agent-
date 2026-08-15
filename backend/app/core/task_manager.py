"""
task_manager.py
High-level interface for creating, tracking, and cancelling async research tasks.
Bridges FastAPI endpoints ↔ Celery workers ↔ JobService persistence.
"""

import logging
import threading
from typing import Optional
from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)


def _celery_worker_available() -> bool:
    try:
        from app.workers.celery_app import celery_app
        ping = celery_app.control.ping(timeout=1.0)
        return bool(ping)
    except Exception:
        return False


def _run_research_inline(job_id: str, query: str) -> None:
    """Fallback when no Celery worker is listening."""
    from app.workers.research_tasks import run_deep_research_task
    run_deep_research_task.run(job_id, query)


class TaskManager:
    def __init__(self):
        self.job_service = get_job_service()

    # ------------------------------------------------------------------ #
    #  Submit a new research task                                          #
    # ------------------------------------------------------------------ #
    def submit_research(self, query: str) -> str:
        """
        Create a job record and dispatch the Celery task.
        Returns the job_id immediately.
        """
        job_id = self.job_service.create_job(query)

        from app.workers.research_tasks import run_deep_research_task

        if _celery_worker_available():
            run_deep_research_task.delay(job_id, query)
            logger.info(f"Research task dispatched to Celery [job={job_id}]")
        else:
            logger.warning(
                f"No Celery worker detected — running research inline [job={job_id}]"
            )
            thread = threading.Thread(
                target=_run_research_inline,
                args=(job_id, query),
                daemon=True,
            )
            thread.start()
        return job_id

    # ------------------------------------------------------------------ #
    #  Query helpers                                                       #
    # ------------------------------------------------------------------ #
    def get_status(self, job_id: str) -> Optional[dict]:
        job = self.job_service.get_job(job_id)
        if not job:
            return None
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "current_step": job.get("current_step", ""),
            "error": job.get("error"),
        }

    def get_result(self, job_id: str) -> Optional[dict]:
        job = self.job_service.get_job(job_id)
        if not job:
            return None
        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "report": job.get("report", ""),
            "sources": job.get("sources", []),
            "quality_metrics": job.get("quality_metrics", {}),
            "research_steps": job.get("research_steps", []),
            "timing": job.get("timing", {}),
            "error": job.get("error"),
        }

    # ------------------------------------------------------------------ #
    #  Cancel                                                              #
    # ------------------------------------------------------------------ #
    def cancel_task(self, job_id: str) -> bool:
        job = self.job_service.get_job(job_id)
        if not job:
            return False
        if job["status"] in ("completed", "failed", "cancelled"):
            return False
        self.job_service.mark_cancelled(job_id)
        logger.info(f"Task cancellation requested [job={job_id}]")
        return True


def get_task_manager() -> TaskManager:
    return TaskManager()
