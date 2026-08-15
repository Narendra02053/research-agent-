"""
job_service.py
Manages job lifecycle: creation, status updates, result storage, and retrieval.
Backs everything to Redis memory for persistence and dashboard readiness.
"""

import time
import uuid
import logging
from typing import Optional
from app.core.memory import get_memory_service

logger = logging.getLogger(__name__)

JOB_PREFIX = "job"


class JobService:
    def __init__(self):
        self.memory = get_memory_service()

    # ------------------------------------------------------------------ #
    #  Create                                                              #
    # ------------------------------------------------------------------ #
    def create_job(self, query: str) -> str:
        """Create a new research job and return the job_id."""
        job_id = str(uuid.uuid4())
        self.memory.save_research_session(f"{JOB_PREFIX}:{job_id}", {
            "job_id": job_id,
            "query": query,
            "status": "pending",
            "progress": 0,
            "current_step": "",
            "created_at": time.time(),
            "updated_at": time.time(),
            "completed_at": None,
            "report": "",
            "sources": [],
            "quality_metrics": {},
            "research_steps": [],
            "timing": {},
            "error": None
        }, ttl=86400)
        logger.info(f"Job created [id={job_id}] query='{query[:60]}'")
        return job_id

    # ------------------------------------------------------------------ #
    #  Read                                                                #
    # ------------------------------------------------------------------ #
    def get_job(self, job_id: str) -> Optional[dict]:
        return self.memory.get_research_session(f"{JOB_PREFIX}:{job_id}")

    # ------------------------------------------------------------------ #
    #  Status updates                                                      #
    # ------------------------------------------------------------------ #
    def mark_running(self, job_id: str, step: str = "", progress: int = 0):
        self._update(job_id, {
            "status": "running",
            "current_step": step,
            "progress": progress
        })

    def update_progress(self, job_id: str, step: str, progress: int):
        self._update(job_id, {
            "current_step": step,
            "progress": min(progress, 99)
        })

    def mark_complete(self, job_id: str, report: str, sources: list,
                      quality_metrics: dict, steps: list, timing: dict):
        self._update(job_id, {
            "status": "completed",
            "progress": 100,
            "current_step": "done",
            "completed_at": time.time(),
            "report": report,
            "sources": sources,
            "quality_metrics": quality_metrics,
            "research_steps": steps,
            "timing": timing
        })
        logger.info(f"Job completed [id={job_id}]")

    def mark_failed(self, job_id: str, error: str, step: str = ""):
        self._update(job_id, {
            "status": "failed",
            "current_step": step,
            "error": error
        })
        logger.error(f"Job failed [id={job_id}] step='{step}' error='{error[:120]}'")

    def mark_cancelled(self, job_id: str):
        self._update(job_id, {"status": "cancelled"})
        logger.info(f"Job cancelled [id={job_id}]")

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #
    def _update(self, job_id: str, data: dict):
        data["updated_at"] = time.time()
        self.memory.update_research_memory(f"{JOB_PREFIX}:{job_id}", data)


def get_job_service() -> JobService:
    return JobService()
