from fastapi import FastAPI
from dotenv import load_dotenv

# Load environment variables (such as TAVILY_API_KEY) from .env
load_dotenv()

from app.routes import research, search, deep_research, agentic_research, mcp_tools, async_research
from app.core.logging_config import configure_logging
from app.mcp import init_mcp

# Configure structured logging for the application
configure_logging()

# Initialize MCP tools
init_mcp()

# Initialize FastAPI app for the AI Deep Research Agent
app = FastAPI(title="AI Deep Research Agent")

# Register routers
app.include_router(research.router)
app.include_router(search.router)
app.include_router(deep_research.router)
app.include_router(agentic_research.router)
app.include_router(mcp_tools.router)
app.include_router(async_research.router)

@app.get("/")
async def root():
    """
    Root endpoint for health check and basic API verification.
    """
    return {"message": "AI Deep Research Agent Running"}
