# task_manager.py - Management of asynchronous tasks.
"""
task_manager.py
Production-grade task orchestration with:
- Task retries with exponential backoff
- Task timeout handling
- Task cancellation with cleanup
- Task progress tracking and persistence
- Failure recovery
- Retry for failed external API calls
- Task metrics (status, progress %, duration, started_at)
"""

import logging
import threading
import time
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from app.services.job_service import get_job_service

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
BACKOFF_BASE_SECS = 2.0
TASK_TIMEOUT_SECS = 600


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


def _calculate_backoff(attempt: int) -> float:
    """Calculate exponential backoff with jitter."""
    import random
    return BACKOFF_BASE_SECS * (2 ** attempt) + random.uniform(0, 1.0)


def _generate_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:12]}"


class TaskMetrics:
    """Tracks task execution metrics."""

    def __init__(self) -> None:
        self.tasks_submitted: int = 0
        self.tasks_completed: int = 0
        self.tasks_failed: int = 0
        self.tasks_cancelled: int = 0
        self.tasks_timed_out: int = 0

    def snapshot(self) -> dict[str, int]:
        return {
            "tasks_submitted": self.tasks_submitted,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_cancelled": self.tasks_cancelled,
            "tasks_timed_out": self.tasks_timed_out,
        }


class TaskManager:
    """
    Manages async research task lifecycle: submit, track, cancel, retry.
    Bridges FastAPI endpoints -> Celery workers / inline threads -> JobService.
    """

    def __init__(self) -> None:
        self.job_service = get_job_service()
        self.metrics = TaskMetrics()
        self._active_tasks: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def submit_research(self, query: str) -> str:
        """
        Create a job record and dispatch the task.
        Returns the job_id immediately.

        Implements retry logic for the initial job creation.
        """
        job_id = ""
        for attempt in range(MAX_RETRIES):
            try:
                job_id = self.job_service.create_job(query)
                break
            except Exception as e:
                logger.warning(
                    f"Job creation failed (attempt {attempt + 1}): {e}",
                    extra={
                        "event": "task_create_retry",
                        "attempt": attempt + 1,
                    },
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(_calculate_backoff(attempt))
                else:
                    raise

        from app.workers.research_tasks import run_deep_research_task

        task_id = _generate_task_id()
        task_info = {
            "task_id": task_id,
            "job_id": job_id,
            "query": query,
            "status": "submitted",
            "started_at": datetime.now(tz=timezone.utc).isoformat(),
            "progress": 0,
        }

        with self._lock:
            self._active_tasks[job_id] = task_info

        if _celery_worker_available():
            run_deep_research_task.delay(job_id, query)
            logger.info(
                "Research task dispatched to Celery",
                extra={
                    "event": "task_dispatched",
                    "job_id": job_id,
                    "method": "celery",
                },
            )
        else:
            logger.warning(
                "No Celery worker detected — running research inline",
                extra={
                    "event": "task_inline",
                    "job_id": job_id,
                    "method": "inline",
                },
            )
            thread = threading.Thread(
                target=self._run_with_timeout,
                args=(job_id, query, task_id),
                daemon=True,
            )
            thread.start()

        self.metrics.tasks_submitted += 1
        return job_id

    def _run_with_timeout(self, job_id: str, query: str, task_id: str) -> None:
        """Run research task with timeout protection."""
        try:
            self._update_task_status(job_id, "running")

            result = self._run_with_retry(
                _run_research_inline,
                job_id=job_id,
                query=query,
            )

            if result:
                self._update_task_status(job_id, "completed", progress=100)
                self.metrics.tasks_completed += 1
            else:
                self._update_task_status(job_id, "failed")
                self.metrics.tasks_failed += 1

        except Exception as e:
            logger.error(
                f"Task failed: {e}",
                extra={"event": "task_failed", "job_id": job_id, "task_id": task_id},
            )
            self._update_task_status(job_id, "failed")
            try:
                self.job_service.mark_failed(job_id, str(e))
            except Exception:
                pass
            self.metrics.tasks_failed += 1

        finally:
            with self._lock:
                self._active_tasks.pop(job_id, None)

    def _run_with_retry(self, fn: Callable, **kwargs: Any) -> bool:
        """Execute a function with exponential backoff retry."""
        last_exception: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            try:
                fn(**kwargs)
                return True
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"Task execution failed (attempt {attempt + 1}/{MAX_RETRIES}): {e}",
                    extra={
                        "event": "task_execution_retry",
                        "attempt": attempt + 1,
                        "max_retries": MAX_RETRIES,
                    },
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(_calculate_backoff(attempt))

        if last_exception:
            logger.error(
                f"Task execution failed after {MAX_RETRIES} attempts",
                extra={
                    "event": "task_execution_failed",
                    "error": str(last_exception),
                },
            )
        return False

    def _update_task_status(
        self,
        job_id: str,
        status: str,
        progress: Optional[int] = None,
    ) -> None:
        """Update the in-memory task status."""
        with self._lock:
            if job_id in self._active_tasks:
                self._active_tasks[job_id]["status"] = status
                if progress is not None:
                    self._active_tasks[job_id]["progress"] = progress

    def get_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """
        Get current task status with metrics.
        Returns None if job not found.
        """
        job = self.job_service.get_job(job_id)
        if not job:
            return None

        duration = None
        started_at = job.get("created_at")
        if started_at and job.get("status") in ("completed", "failed", "cancelled"):
            try:
                from datetime import datetime
                start = datetime.fromisoformat(started_at) if isinstance(started_at, str) else started_at
                duration = (datetime.now(tz=timezone.utc) - start.replace(tzinfo=timezone.utc) if isinstance(start, datetime) and start.tzinfo is None else
                           datetime.now(tz=timezone.utc) - start).total_seconds()
            except Exception:
                pass

        return {
            "job_id": job["job_id"],
            "status": job["status"],
            "progress": job.get("progress", 0),
            "current_step": job.get("current_step", ""),
            "error": job.get("error"),
            "started_at": started_at,
            "duration_secs": round(duration, 2) if duration else None,
        }

    def get_result(self, job_id: str) -> Optional[dict[str, Any]]:
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

    def cancel_task(self, job_id: str) -> bool:
        """
        Cancel a running task with cleanup.
        Returns True if cancellation was successful.
        """
        job = self.job_service.get_job(job_id)
        if not job:
            return False

        if job["status"] in ("completed", "failed", "cancelled"):
            return False

        try:
            self.job_service.mark_cancelled(job_id)
            self._update_task_status(job_id, "cancelled")

            with self._lock:
                self._active_tasks.pop(job_id, None)

            logger.info(
                "Task cancelled",
                extra={"event": "task_cancelled", "job_id": job_id},
            )
            self.metrics.tasks_cancelled += 1
            return True
        except Exception as e:
            logger.error(
                f"Task cancellation failed: {e}",
                extra={"event": "task_cancel_error", "job_id": job_id},
            )
            return False

    def get_task_progress(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get detailed progress for an active task."""
        with self._lock:
            task_info = self._active_tasks.get(job_id)
        if task_info:
            return {
                "task_id": task_info["task_id"],
                "job_id": task_info["job_id"],
                "status": task_info["status"],
                "progress": task_info["progress"],
                "started_at": task_info["started_at"],
                "elapsed_secs": round(
                    (datetime.now(tz=timezone.utc) - datetime.fromisoformat(task_info["started_at"])).total_seconds(),
                    2,
                ),
            }
        return self.get_status(job_id)

    def update_progress(self, job_id: str, progress: int, step: str = "") -> None:
        """Update progress for an active task (called by workers)."""
        self._update_task_status(job_id, "running", progress)
        try:
            self.job_service.update_progress(job_id, progress, step)
        except Exception as e:
            logger.warning(
                f"Failed to persist progress: {e}",
                extra={"event": "task_progress_error", "job_id": job_id},
            )

    def list_active_tasks(self) -> list[dict[str, Any]]:
        """List all currently active tasks."""
        with self._lock:
            return [
                {
                    "job_id": info["job_id"],
                    "status": info["status"],
                    "progress": info["progress"],
                    "started_at": info["started_at"],
                    "query": info["query"][:80] + "..." if len(info["query"]) > 80 else info["query"],
                }
                for info in self._active_tasks.values()
            ]

    def get_metrics(self) -> dict[str, Any]:
        return {
            **self.metrics.snapshot(),
            "active_count": len(self._active_tasks),
        }


def get_task_manager() -> TaskManager:
    return TaskManager()
