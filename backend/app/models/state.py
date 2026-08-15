from typing import TypedDict, List, Dict, Any

class ResearchState(TypedDict):
    """
    State structure for the LangGraph research workflow.
    """
    query: str
    search_queries: List[str]
    search_results: List[Dict[str, Any]]
    extracted_content: List[Dict[str, Any]]
    retrieved_chunks: List[Dict[str, Any]]
    reranked_chunks: List[Dict[str, Any]]
    context: str
    intermediate_analysis: str
    final_answer: str
    sources: List[Dict[str, str]]
    research_steps: List[str]
    quality_metrics: Dict[str, Any]
