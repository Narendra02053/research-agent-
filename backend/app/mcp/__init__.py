# __init__.py - Initialization for the Model Context Protocol module.
from app.mcp.tool_registry import get_tool_registry
from app.mcp.tools.search_tool import SearchTool
from app.mcp.tools.extraction_tool import ExtractionTool
from app.mcp.tools.retrieval_tool import RetrievalTool
from app.mcp.tools.rerank_tool import RerankTool
from app.mcp.tools.report_tool import ReportTool

def init_mcp():
    """
    Register all available MCP tools in the global registry.
    Should be called during application startup.
    """
    registry = get_tool_registry()
    
    # Register core research tools
    registry.register_tool(SearchTool())
    registry.register_tool(ExtractionTool())
    registry.register_tool(RetrievalTool())
    registry.register_tool(RerankTool())
    registry.register_tool(ReportTool())
    
    # Future tools (browser, filesystem, etc.) can be registered here.
