import logging
from app.models.state import ResearchState
from app.mcp.tool_executor import get_tool_executor
from app.services.indexing_service import get_indexing_service
from app.services.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

def retrieval_node(state: ResearchState) -> dict:
    logger.info("--- RETRIEVAL AGENT ---")
    executor = get_tool_executor()
    indexer = get_indexing_service()
    
    search_results = state.get("search_results", [])
    query = state["query"]
    
    # 1. Extraction (Using MCP extraction_tool)
    logger.info("Extracting webpage content...")
    extracted = []
    for res in search_results:
        try:
            content = executor.execute_tool("extraction_tool", {"url": res["url"]})
            extracted.append({
                "title": res["title"],
                "url": res["url"],
                "content": content if content else res.get("content_snippet", "")
            })
        except Exception as e:
            logger.warning(f"Failed to extract from {res['url']}: {e}")
            
    state["extracted_content"] = extracted
    
    # 2. Indexing
    try:
        indexer.index_search_results(extracted)
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")
        
    # 3. Retrieval (Using MCP retrieval_tool)
    logger.info("Retrieving semantic chunks...")
    retrieved = executor.execute_tool("retrieval_tool", {"query": query, "limit": 15})
    state["retrieved_chunks"] = retrieved
    
    # 4. Reranking (Using MCP rerank_tool)
    logger.info("Reranking chunks...")
    reranked = executor.execute_tool("rerank_tool", {"query": query, "chunks": retrieved, "top_k": 8})
    state["reranked_chunks"] = reranked
    
    # 5. Build Context
    context = ContextBuilder.build_research_context(query, reranked)
    state["context"] = context
    
    # Track final sources
    sources = []
    seen = set()
    for chunk in reranked:
        url = chunk["metadata"].get("url")
        if url and url not in seen:
            seen.add(url)
            sources.append({
                "title": chunk["metadata"].get("title", "Unknown"),
                "url": url
            })
            
    state["sources"] = sources
    
    step_msg = "Retrieval Agent extracted content, indexed to Qdrant, retrieved semantic chunks, and reranked context."
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps
    
    return state
