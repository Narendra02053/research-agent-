from typing import Dict, List, Any
from app.mcp.base_tool import BaseTool

class ToolRegistry:
    """
    Registry for dynamically loaded MCP-style tools.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, BaseTool] = {}
        return cls._instance
        
    def register_tool(self, tool: BaseTool):
        self._tools[tool.name] = tool
        
    def get_tool(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise ValueError(f"Tool '{name}' not found in registry.")
        return self._tools[name]
        
    def get_all_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema,
                "output_schema": t.output_schema
            }
            for t in self._tools.values()
        ]

def get_tool_registry() -> ToolRegistry:
    return ToolRegistry()
