from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List
import logging

from app.mcp.tool_registry import get_tool_registry
from app.mcp.tool_executor import get_tool_executor

router = APIRouter(prefix="/mcp", tags=["MCP Tools"])
logger = logging.getLogger(__name__)

class ToolExecutionRequest(BaseModel):
    tool_name: str
    input: Dict[str, Any]

@router.get("/tools", response_model=Dict[str, List[Dict[str, Any]]])
async def list_tools():
    """
    Returns a list of all dynamically registered MCP tools,
    including their descriptions and JSON schemas for inputs.
    """
    registry = get_tool_registry()
    return {"tools": registry.get_all_tools()}

@router.post("/execute-tool")
async def execute_tool(request: ToolExecutionRequest):
    """
    Dynamically execute a specified tool by name with the given inputs.
    """
    executor = get_tool_executor()
    try:
        result = executor.execute_tool(request.tool_name, request.input)
        return {"status": "success", "tool_name": request.tool_name, "result": result}
    except Exception as e:
        logger.error(f"Endpoint execute_tool failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
