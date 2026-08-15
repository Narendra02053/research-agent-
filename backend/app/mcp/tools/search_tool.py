# search_tool.py - MCP tool for searching information.
from typing import Any
from app.mcp.base_tool import BaseTool
from app.services.search_service import get_search_service

class SearchTool(BaseTool):
    name = "search_tool"
    description = "Perform a web search using Tavily to gather relevant internet sources."
    input_schema = {
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"]
    }
    output_schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "url": {"type": "string"},
                "content_snippet": {"type": "string"}
            }
        }
    }
    
    def __init__(self):
        self.search_service = get_search_service()
        
    def execute(self, query: str) -> Any:
        return self.search_service.search_web(query)
