import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.state import ResearchState
from app.mcp.tool_executor import get_tool_executor
from app.services.indexing_service import get_indexing_service
from app.services.context_builder import ContextBuilder
from app.core.config import settings

logger = logging.getLogger(__name__)


def _extract_one(executor, result: dict) -> dict:
    try:
        content = executor.execute_tool("extraction_tool", {"url": result["url"]})
        return {
            "title": result["title"],
            "url": result["url"],
            "content": content if content else result.get("content_snippet", ""),
        }
    except Exception as e:
        logger.warning(f"Failed to extract from {result['url']}: {e}")
        return {
            "title": result["title"],
            "url": result["url"],
            "content": result.get("content_snippet", ""),
        }


def retrieval_node(state: ResearchState) -> dict:
    logger.info("--- RETRIEVAL AGENT ---")
    executor = get_tool_executor()
    indexer = get_indexing_service()

    search_results = state.get("search_results", [])[: settings.MAX_EXTRACTION_URLS]
    query = state["query"]
    job_id = state.get("job_id", "")

    # 1. Parallel extraction
    logger.info(f"Extracting content from {len(search_results)} URLs (parallel)...")
    extracted = []
    if search_results:
        max_workers = min(5, len(search_results))
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [
                pool.submit(_extract_one, executor, res) for res in search_results
            ]
            for future in as_completed(futures):
                extracted.append(future.result())

    state["extracted_content"] = extracted

    # 2. Indexing
    try:
        indexer.index_search_results(extracted)
    except Exception as e:
        logger.error(f"Indexing failed: {str(e)}")

    # 3. Retrieval
    logger.info("Retrieving semantic chunks...")
    retrieved = executor.execute_tool(
        "retrieval_tool", {"query": query, "limit": settings.RETRIEVAL_CHUNK_LIMIT}
    )
    state["retrieved_chunks"] = retrieved

    # 4. Reranking
    logger.info("Reranking chunks...")
    reranked = executor.execute_tool(
        "rerank_tool",
        {"query": query, "chunks": retrieved, "top_k": settings.RERANK_TOP_K},
    )
    state["reranked_chunks"] = reranked

    # 5. Knowledge Graph (optional — adds multiple LLM calls per chunk)
    kg_context_text = ""
    kg_snapshot = {"nodes": [], "edges": []}
    if settings.ENABLE_KNOWLEDGE_GRAPH:
        try:
            from app.knowledge_graph.research_memory_graph import get_research_memory

            memory = get_research_memory()
            chunks_for_kg = (reranked + extracted)[: settings.MAX_KG_CHUNKS]
            ingest_result = memory.ingest_research_chunks(
                chunks_for_kg, query=query, session_id=job_id
            )
            logger.info(
                f"Knowledge Graph updated: +{ingest_result['nodes_added']} nodes, "
                f"+{ingest_result['edges_added']} edges"
            )

            kg_result = memory.get_graph_context_with_meta(query)
            kg_context_text = kg_result.get("context_text", "")
            kg_snapshot = {
                "nodes": kg_result.get("nodes", []),
                "edges": kg_result.get("edges", []),
            }
        except Exception as e:
            logger.error(f"Knowledge graph integration failed (non-fatal): {e}")
    else:
        logger.info("Knowledge graph skipped (ENABLE_KNOWLEDGE_GRAPH=false)")

    # 6. Build context
    context = ContextBuilder.build_research_context(query, reranked)
    if kg_context_text:
        context = f"{kg_context_text}\n\n{context}"
    state["context"] = context
    state["knowledge_graph"] = kg_snapshot

    sources = []
    seen = set()
    for chunk in reranked:
        url = chunk["metadata"].get("url")
        if url and url not in seen:
            seen.add(url)
            sources.append({
                "title": chunk["metadata"].get("title", "Unknown"),
                "url": url,
            })

    state["sources"] = sources

    step_msg = (
        "Retrieval Agent extracted content in parallel, indexed to Qdrant, "
        "retrieved semantic chunks, and reranked context."
    )
    steps = state.get("research_steps", [])
    steps.append(step_msg)
    state["research_steps"] = steps

    return state
