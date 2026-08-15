"""
api_models.py
Standardized API request and response wrappers.
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")

class ResponseMetadata(BaseModel):
    execution_time: str
    request_id: str

class StandardResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    metadata: Optional[ResponseMetadata] = None

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    services: dict
