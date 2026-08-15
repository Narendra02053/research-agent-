"""
research_memory_graph.py
Singleton manager for persistent long-term research memory across sessions.

Connects research sessions over time by merging new findings into the
persistent historical memory graph. Provides session-scoped graph snapshots
for API delivery and WebSocket broadcasting.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from app.knowledge_graph.graph_builder import GraphBuilder, get_graph_builder
from app.knowledge_graph.graph_query_engine import GraphQueryEngine, get_graph_query_engine
from app.knowledge_graph.graph_store import get_graph_store

logger = logging.getLogger(__name__)


class ResearchMemoryGraph:
    """
    Singleton manager that acts as the bridge between individual research
    sessions and the persistent long-term knowledge graph.

    Usage in the research pipeline:
        memory = get_research_memory()
        # After retrieval, ingest chunks
        summary = memory.ingest_research_chunks(chunks, query)
        # Get formatted context for synthesis prompt
        kg_context = memory.get_context_for_query(query)
        # Get snapshot for API/frontend
        snapshot = memory.get_snapshot()
    """

    def __init__(self):
        self._builder: GraphBuilder = get_graph_builder()
        self._query_engine: GraphQueryEngine = get_graph_query_engine()
        self._store = get_graph_store()
        self._session_stats: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    #  Ingestion                                                            #
    # ------------------------------------------------------------------ #

    def ingest_research_chunks(
        self,
        chunks: List[Dict[str, Any]],
        query: str = "",
        session_id: str = "",
    ) -> Dict[str, Any]:
        """
        Process retrieved/extracted research chunks and merge into the memory graph.

        Args:
            chunks: List of chunk dicts from the RAG pipeline
                    Each must have 'content'/'text' and optionally 'metadata.url'
            query: The original research query (for logging)
            session_id: Optional job/session id for tracking

        Returns:
            Summary dict: {'nodes_added': int, 'edges_added': int, 'graph_stats': {...}}
        """
        if not chunks:
            logger.info("[ResearchMemory] No chunks to ingest.")
            return {"nodes_added": 0, "edges_added": 0, "graph_stats": self._store.stats()}

        start = time.perf_counter()
        result = self._builder.process_chunks(chunks)
        elapsed = round(time.perf_counter() - start, 2)

        stats = self._store.stats()
        self._session_stats[session_id or "latest"] = {
            "query": query[:100],
            "nodes_added": result["nodes_added"],
            "edges_added": result["edges_added"],
            "elapsed_seconds": elapsed,
            "graph_total_nodes": stats["node_count"],
            "graph_total_edges": stats["edge_count"],
            "timestamp": time.time(),
        }

        logger.info(
            f"[ResearchMemory] Ingested: +{result['nodes_added']} nodes, "
            f"+{result['edges_added']} edges in {elapsed}s "
            f"(graph total: {stats['node_count']} nodes, {stats['edge_count']} edges)"
        )
        return {**result, "graph_stats": stats}

    # ------------------------------------------------------------------ #
    #  Query                                                                #
    # ------------------------------------------------------------------ #

    def get_context_for_query(
        self, query: str, max_hops: int = 2, top_k: int = 6
    ) -> str:
        """
        Return a formatted KNOWLEDGE GRAPH CONTEXT string for LLM injection.
        Returns empty string if the graph has no relevant entities.
        """
        result = self._query_engine.query_context_for_research(
            query, max_hops=max_hops, top_k=top_k
        )
        return result.get("context_text", "")

    def get_graph_context_with_meta(
        self, query: str, max_hops: int = 2, top_k: int = 6
    ) -> Dict[str, Any]:
        """
        Extended version of get_context_for_query that also returns
        raw node/edge data for WebSocket broadcasting and API delivery.
        """
        return self._query_engine.query_context_for_research(
            query, max_hops=max_hops, top_k=top_k
        )

    # ------------------------------------------------------------------ #
    #  Snapshot / Stats                                                     #
    # ------------------------------------------------------------------ #

    def get_snapshot(self) -> Dict[str, Any]:
        """Return the full serializable graph for API responses and frontend visualizer."""
        return self._builder.get_graph_snapshot()

    def get_stats(self) -> Dict[str, Any]:
        """Return graph statistics and recent session info."""
        return {
            "graph_stats": self._store.stats(),
            "recent_sessions": list(self._session_stats.values())[-5:],
        }

    def reset(self):
        """Clear the entire memory graph (admin/debug use only)."""
        self._store.clear()
        self._session_stats.clear()
        logger.warning("[ResearchMemory] Memory graph has been reset.")

    def save(self):
        """Manually trigger graph persistence."""
        self._store.save()


# ------------------------------------------------------------------ #
#  Module-level singleton                                              #
# ------------------------------------------------------------------ #
_research_memory_instance: Optional[ResearchMemoryGraph] = None


def get_research_memory() -> ResearchMemoryGraph:
    global _research_memory_instance
    if _research_memory_instance is None:
        _research_memory_instance = ResearchMemoryGraph()
    return _research_memory_instance
