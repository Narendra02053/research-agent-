# rerank_tool.py - MCP tool for document reranking.
from typing import Any, List, Dict
from app.mcp.base_tool import BaseTool
from app.rag.reranker import get_reranker_service

class RerankTool(BaseTool):
    name = "rerank_tool"
    description = "Rerank retrieved semantic chunks using a cross-encoder to optimize evidence quality."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "chunks": {"type": "array"},
            "top_k": {"type": "integer"}
        },
        "required": ["query", "chunks"]
    }
    output_schema = {"type": "array"}
    
    def __init__(self):
        self.reranker = get_reranker_service()
        
    def execute(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> Any:
        return self.reranker.rerank_results(query, chunks, top_k=top_k)
