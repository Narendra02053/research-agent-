from typing import Any
from app.mcp.base_tool import BaseTool
from app.services.extraction_service import get_extraction_service

class ExtractionTool(BaseTool):
    name = "extraction_tool"
    description = "Extract and clean readable text from a webpage URL using Trafilatura."
    input_schema = {
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"]
    }
    output_schema = {"type": "string"}
    
    def __init__(self):
        self.extraction_service = get_extraction_service()
        
    def execute(self, url: str) -> Any:
        return self.extraction_service.extract_webpage_content(url)
