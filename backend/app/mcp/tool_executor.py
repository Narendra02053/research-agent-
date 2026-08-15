# tool_executor.py - Executes MCP tools.
import logging
from typing import Any, Dict
from app.core.logging_config import timed
from app.mcp.tool_registry import get_tool_registry

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Dynamically executes tools by name, passing validated inputs.
    """
    def __init__(self):
        self.registry = get_tool_registry()
        
    @timed("MCP Tool Execution")
    def execute_tool(self, tool_name: str, kwargs: Dict[str, Any]) -> Any:
        logger.info(f"Executing tool: {tool_name}")
        try:
            tool = self.registry.get_tool(tool_name)
            result = tool.execute(**kwargs)
            logger.info(f"Tool '{tool_name}' executed successfully.")
            return result
        except Exception as e:
            logger.error(f"Tool '{tool_name}' execution failed: {e}")
            raise e

def get_tool_executor() -> ToolExecutor:
    return ToolExecutor()
