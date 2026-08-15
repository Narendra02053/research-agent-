"""
job_models.py
Pydantic models for research jobs, task metadata, execution metrics, and failure reports.
"""

from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class JobMetadata(BaseModel):
    job_id: str
    query: str
    status: str = "pending"           # pending | running | completed | failed | cancelled
    progress: int = 0                 # 0-100
    current_step: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    completed_at: Optional[float] = None


class JobResult(BaseModel):
    job_id: str
    status: str
    report: str = ""
    sources: List[Dict[str, str]] = []
    quality_metrics: Dict[str, Any] = {}
    research_steps: List[str] = []
    timing: Dict[str, float] = {}
    error: Optional[str] = None


class JobSubmitResponse(BaseModel):
    job_id: str
    status: str = "pending"


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    current_step: str = ""
    error: Optional[str] = None


class JobFailureReport(BaseModel):
    job_id: str
    error: str
    failed_step: str = ""
    timestamp: float = 0.0
