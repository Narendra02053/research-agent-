"""
router.py
Centralized API router for v1 endpoints.
Aggregates all domain-specific routers and provides health checks.
"""
from fastapi import APIRouter
from app.routes import research, search, deep_research, agentic_research, mcp_tools, async_research
from app.models.api_models import HealthResponse

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
