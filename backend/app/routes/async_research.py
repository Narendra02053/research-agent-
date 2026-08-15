# async_research.py - API endpoints for asynchronous research.
"""
async_research.py
Async-first research endpoints.
POST /async-research  → submit job, returns job_id immediately
GET  /research-status/{job_id}  → poll progress
GET  /research-result/{job_id}  → fetch completed result
POST /research-cancel/{job_id}  → cancel a running job
"""

import logging
from fastapi import APIRouter, HTTPException

from app.models.job_models import (
    JobSubmitResponse,
    JobStatusResponse,
    JobResult,
)
from app.core.task_manager import get_task_manager
from pydantic import BaseModel

router = APIRouter(tags=["Async Research"])
logger = logging.getLogger(__name__)


class AsyncResearchRequest(BaseModel):
    query: str


# ------------------------------------------------------------------ #
#  Submit                                                              #
# ------------------------------------------------------------------ #
@router.post("/async-research", response_model=JobSubmitResponse)
async def submit_async_research(request: AsyncResearchRequest):
    """
    Submit a research query for background execution.
    Returns a job_id immediately; the work runs in a Celery worker.
    """
    manager = get_task_manager()
    job_id = manager.submit_research(request.query)
    return JobSubmitResponse(job_id=job_id, status="pending")


# ------------------------------------------------------------------ #
#  Status                                                              #
# ------------------------------------------------------------------ #
@router.get("/research-status/{job_id}", response_model=JobStatusResponse)
async def get_research_status(job_id: str):
    """
    Poll the current status and progress of a research job.
    """
    manager = get_task_manager()
    status = manager.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return JobStatusResponse(**status)


# ------------------------------------------------------------------ #
#  Result                                                              #
# ------------------------------------------------------------------ #
@router.get("/research-result/{job_id}", response_model=JobResult)
async def get_research_result(job_id: str):
    """
    Retrieve the full result of a completed research job.
    """
    manager = get_task_manager()
    result = manager.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if result["status"] not in ("completed", "failed"):
        raise HTTPException(status_code=202, detail="Job is still in progress.")
    return JobResult(**result)


# ------------------------------------------------------------------ #
#  Cancel                                                              #
# ------------------------------------------------------------------ #
@router.post("/research-cancel/{job_id}")
async def cancel_research(job_id: str):
    """
    Request cancellation of a running research job.
    """
    manager = get_task_manager()
    success = manager.cancel_task(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled (not found or already finished).")
    return {"job_id": job_id, "status": "cancelled"}
