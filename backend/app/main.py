from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.api.v1.router import api_router
from app.core.logging_config import configure_logging
from app.core.config import settings
from app.mcp import init_mcp
from app.middleware.request_logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware

# Configure structured logging for the application
configure_logging()

# Initialize MCP tools
init_mcp()

# Initialize FastAPI app with production configurations
app = FastAPI(
    title="AI Deep Research Agent",
    description="Scalable, asynchronous AI Research Platform API",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Add Middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# Register central API v1 router
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    """
    Root endpoint.
    """
    return {
        "message": "AI Deep Research Agent API",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs"
    }
