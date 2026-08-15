from typing import Any, List, Dict
from app.mcp.base_tool import BaseTool
from app.core.llm import get_llm_service

class ReportTool(BaseTool):
    name = "report_tool"
    description = "Generate a structured, citation-aware research report using a grounded LLM."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "analysis": {"type": "string"},
            "sources": {"type": "array"}
        },
        "required": ["query", "analysis", "sources"]
    }
    output_schema = {"type": "string"}
    
    def __init__(self):
        self.llm = get_llm_service()
        
    def execute(self, query: str, analysis: str, sources: List[Dict[str, str]]) -> Any:
        sources_text = "\n".join([f"- {s['title']}: {s['url']}" for s in sources])
        prompt = f"""
You are an expert AI Research Report Writer.
Using the intermediate analysis provided, generate a final, highly-professional research report.

REQUIREMENTS:
- Be concise but highly informative.
- Include structured sections.
- Cite your sources inline.
- Format beautifully in Markdown.

USER QUERY: {query}

INTERMEDIATE ANALYSIS:
{analysis}

SOURCES AVAILABLE FOR CITATION:
{sources_text}

FINAL REPORT:
"""
        return self.llm.generate_response(prompt)
