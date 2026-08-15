# retrieval_tool.py - MCP tool for document retrieval.
from typing import Any
from app.mcp.base_tool import BaseTool
from app.rag.vector_store import get_vector_store

class RetrievalTool(BaseTool):
    name = "retrieval_tool"
    description = "Retrieve the top semantically relevant chunks from the Qdrant vector database."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"}
        },
        "required": ["query"]
    }
    output_schema = {"type": "array"}
    
    def __init__(self):
        self.vector_store = get_vector_store()
        
    def execute(self, query: str, limit: int = 15) -> Any:
        return self.vector_store.search_similar_content(query, limit=limit)
