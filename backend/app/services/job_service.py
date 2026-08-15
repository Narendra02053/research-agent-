"""
job_service.py
Manages job lifecycle: creation, status updates, result storage, and retrieval.
Backs everything to Redis memory for persistence and dashboard readiness.
"""

import time
import uuid
import logging
import asyncio
from typing import Optional
from app.core.memory import get_memory_service
from app.realtime.stream_service import get_stream_service

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
        
        # Publish creation event asynchronously without blocking
        stream = get_stream_service()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(stream.publish_event(job_id, "workflow_started", {"query": query}))
        except RuntimeError:
            asyncio.run(stream.publish_event(job_id, "workflow_started", {"query": query}))
            
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
        self._publish_update(job_id, f"{step}_started", {"progress": progress, "step": step})

    def update_progress(self, job_id: str, step: str, progress: int):
        self._update(job_id, {
            "current_step": step,
            "progress": min(progress, 99)
        })
        self._publish_update(job_id, "progress_update", {"progress": progress, "step": step})

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
        self._publish_update(job_id, "workflow_finished", {
            "report": report,
            "sources": sources,
            "metrics": quality_metrics
        })

    def mark_failed(self, job_id: str, error: str, step: str = ""):
        self._update(job_id, {
            "status": "failed",
            "current_step": step,
            "error": error
        })
        logger.error(f"Job failed [id={job_id}] step='{step}' error='{error[:120]}'")
        self._publish_update(job_id, "workflow_failed", {"error": error, "step": step})

    def mark_cancelled(self, job_id: str):
        self._update(job_id, {"status": "cancelled"})
        logger.info(f"Job cancelled [id={job_id}]")
        self._publish_update(job_id, "workflow_cancelled", {})

    def _publish_update(self, job_id: str, event_type: str, data: dict):
        stream = get_stream_service()
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(stream.publish_event(job_id, event_type, data))
        except RuntimeError:
            asyncio.run(stream.publish_event(job_id, event_type, data))

    # ------------------------------------------------------------------ #
    #  Internal                                                            #
    # ------------------------------------------------------------------ #
    def _update(self, job_id: str, data: dict):
        data["updated_at"] = time.time()
        self.memory.update_research_memory(f"{JOB_PREFIX}:{job_id}", data)


def get_job_service() -> JobService:
    return JobService()
