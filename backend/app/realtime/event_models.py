# event_models.py - Models for real-time WebSocket events.
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

class StreamEvent(BaseModel):
    event_type: str = Field(..., description="Type of the event, e.g., 'workflow_started', 'planning_completed'")
    job_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(..., description="Unix timestamp of the event")

class TokenChunkEvent(StreamEvent):
    event_type: str = "token_chunk"
    data: Dict[str, Any] = Field(..., description="Must contain 'chunk' string")
