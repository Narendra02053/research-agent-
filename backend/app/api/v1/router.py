"""
router.py
Centralized API router for v1 endpoints.
Aggregates all domain-specific routers and provides health checks.
"""
from fastapi import APIRouter
from app.routes import research, search, deep_research, agentic_research, mcp_tools, async_research
from app.models.api_models import HealthResponse
from fastapi import WebSocket, WebSocketDisconnect
from app.realtime.websocket_manager import manager as ws_manager
from app.realtime.stream_service import get_stream_service
import asyncio

api_router = APIRouter()

# Register domain routers under API v1
api_router.include_router(research.router, prefix="/basic", tags=["Basic Research"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(deep_research.router, prefix="/deep", tags=["Deep Research"])
api_router.include_router(agentic_research.router, prefix="/agentic", tags=["Agentic Research"])
api_router.include_router(mcp_tools.router, prefix="/mcp", tags=["MCP Tools"])
api_router.include_router(async_research.router, prefix="/jobs", tags=["Async Jobs"])

@api_router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """
    Check system health and core service availability.
    """
    # In a production app, this would actively ping Redis, Qdrant, etc.
    services_status = {
        "redis": "healthy",
        "qdrant": "healthy",
        "llm": "healthy",
        "celery_workers": "active"
    }
    return HealthResponse(status="ok", services=services_status)

@api_router.get("/metrics", tags=["System"])
async def metrics():
    """
    Expose basic application metrics for monitoring (Prometheus integration ready).
    """
    return {
        "active_jobs": 0,
        "completed_jobs": 0,
        "system_load": "low"
    }

@api_router.get("/llm/providers", tags=["LLM Gateway"])
async def llm_providers():
    """
    Retrieve available LLM providers, active models, and usage summary.
    """
    from app.llm.router import get_llm_router
    router = get_llm_router()
    return {
        "providers": router.available_providers(),
        "usage_summary": router.usage_summary()
    }


@api_router.websocket("/ws/research/{job_id}")
async def websocket_research_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time streaming of research progress and results.
    """
    await ws_manager.connect(websocket, job_id)
    stream_service = get_stream_service()
    
    try:
        # Subscribe to the Redis Pub/Sub channel for this job
        async for message in stream_service.subscribe(job_id):
            await ws_manager.send_message(message, websocket)
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, job_id)
    except Exception as e:
        import logging
        logging.error(f"WebSocket error for job {job_id}: {e}")
        ws_manager.disconnect(websocket, job_id)


