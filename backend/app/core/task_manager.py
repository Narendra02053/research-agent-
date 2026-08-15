"""
task_manager.py
High-level interface for creating, tracking, and cancelling async research tasks.
Bridges FastAPI endpoints ↔ Celery workers ↔ JobService persistence.
"""

import logging
from typing import Optional
from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)


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

        # Import here to avoid circular imports at module load
        from app.workers.research_tasks import run_deep_research_task
        run_deep_research_task.delay(job_id, query)

        logger.info(f"Research task dispatched [job={job_id}]")
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
            "current_step": job.get("current_step", "")
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
            "timing": job.get("timing", {})
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
