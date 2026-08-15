"""
graph_query_engine.py
Semantic keyword-to-entity lookup and neighborhood analysis for knowledge graph.

Provides:
- Query entity resolution (keywords → matching graph nodes)
- 1-hop / 2-hop neighborhood traversal
- Context formatting for LLM synthesis (KNOWLEDGE GRAPH CONTEXT block)
"""

import logging
from typing import Any, Dict, List, Optional

from app.knowledge_graph.graph_store import GraphNode, get_graph_store

logger = logging.getLogger(__name__)


class GraphQueryEngine:
    """
    High-level query interface for the research knowledge graph.
    Resolves natural language queries to graph neighborhoods and
    formats structured context for LLM synthesis.
    """

    def __init__(self):
        self._store = get_graph_store()

    # ------------------------------------------------------------------ #
    #  Core Query Methods                                                  #
    # ------------------------------------------------------------------ #

    def find_entities_for_query(
        self, query: str, top_k: int = 8
    ) -> List[GraphNode]:
        """
        Resolve a research query to the most relevant graph nodes.
        Uses keyword search across names, aliases, and descriptions.
        """
        words = [w for w in query.split() if len(w) > 3]
        scored: Dict[str, float] = {}

        for word in words:
            hits = self._store.search_nodes(word, top_k=top_k)
            for node in hits:
                scored[node.id] = scored.get(node.id, 0.0) + node.confidence

        # Sort by accumulated relevance score
        ranked_ids = sorted(scored, key=lambda k: scored[k], reverse=True)
        results = []
        for nid in ranked_ids[:top_k]:
            node = self._store.get_node(nid)
            if node:
                results.append(node)

        logger.info(f"[GraphQuery] Query '{query[:60]}' resolved to {len(results)} entities.")
        return results

    def get_neighborhood(
        self,
        entity_names: List[str],
        max_hops: int = 2,
    ) -> Dict[str, Any]:
        """
        Get the combined neighborhood sub-graph for a list of entity names.
        Merges multiple BFS traversals deduplicating nodes/edges.
        """
        all_nodes: Dict[str, Dict] = {}
        all_edges: Dict[str, Dict] = {}

        for name in entity_names:
            # Normalize to node id
            import re
            node_id = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
            sub = self._store.get_neighbors(node_id, max_hops=max_hops)
            for n in sub["nodes"]:
                all_nodes[n["id"]] = n
            for e in sub["edges"]:
                all_edges[e["id"]] = e

        return {
            "nodes": list(all_nodes.values()),
            "edges": list(all_edges.values()),
            "entity_count": len(all_nodes),
            "relation_count": len(all_edges),
        }

    def query_context_for_research(
        self, query: str, max_hops: int = 2, top_k: int = 6
    ) -> Dict[str, Any]:
        """
        Main entry point for the RAG pipeline integration.
        Returns a dict with:
        - 'context_text': formatted KNOWLEDGE GRAPH CONTEXT string for the LLM
        - 'nodes': raw node list
        - 'edges': raw edge list
        """
        # 1. Find relevant anchor entities
        anchor_nodes = self.find_entities_for_query(query, top_k=top_k)
        if not anchor_nodes:
            return {"context_text": "", "nodes": [], "edges": []}

        anchor_names = [n.name for n in anchor_nodes]

        # 2. Expand neighborhood
        neighborhood = self.get_neighborhood(anchor_names, max_hops=max_hops)

        # 3. Format context text
        context_text = self._format_context(
            anchor_nodes, neighborhood
        )

        return {
            "context_text": context_text,
            "nodes": neighborhood["nodes"],
            "edges": neighborhood["edges"],
            "anchor_entities": anchor_names,
        }

    # ------------------------------------------------------------------ #
    #  Context Formatting                                                  #
    # ------------------------------------------------------------------ #

    def _format_context(
        self,
        anchor_nodes: List[GraphNode],
        neighborhood: Dict[str, Any],
    ) -> str:
        """
        Format the graph neighborhood as a structured text block
        for injection into the LLM synthesis prompt.
        """
        if not anchor_nodes:
            return ""

        lines = ["=== KNOWLEDGE GRAPH CONTEXT ===\n"]

        # Anchor entities section
        lines.append("KEY ENTITIES:")
        for node in anchor_nodes[:8]:
            line = f"  • [{node.entity_type.upper()}] {node.name}"
            if node.description:
                line += f" — {node.description}"
            lines.append(line)

        # Relationships section
        edges = neighborhood.get("edges", [])
        if edges:
            lines.append("\nKNOWN RELATIONSHIPS:")
            # Build a node id→name lookup
            node_map = {n["id"]: n["name"] for n in neighborhood.get("nodes", [])}
            seen = set()
            for edge in sorted(edges, key=lambda e: e.get("confidence", 0), reverse=True)[:15]:
                src_name = node_map.get(edge["source_id"], edge["source_id"])
                tgt_name = node_map.get(edge["target_id"], edge["target_id"])
                rel = edge["relation_type"].replace("_", " ")
                key = f"{src_name}|{rel}|{tgt_name}"
                if key in seen:
                    continue
                seen.add(key)
                desc = edge.get("description", "")
                line = f"  • {src_name} [{rel}] {tgt_name}"
                if desc:
                    line += f" — {desc[:100]}"
                lines.append(line)

        # Extended entities from neighborhood
        all_node_names = {n["name"] for n in neighborhood.get("nodes", [])}
        extra = all_node_names - {n.name for n in anchor_nodes}
        if extra:
            lines.append(f"\nRELATED ENTITIES: {', '.join(list(extra)[:12])}")

        lines.append("\n=== END KNOWLEDGE GRAPH CONTEXT ===")
        return "\n".join(lines)

    def graph_stats(self) -> Dict[str, int]:
        """Return basic statistics about the knowledge graph."""
        return self._store.stats()


# Module-level singleton
_query_engine_instance: Optional[GraphQueryEngine] = None


def get_graph_query_engine() -> GraphQueryEngine:
    global _query_engine_instance
    if _query_engine_instance is None:
        _query_engine_instance = GraphQueryEngine()
    return _query_engine_instance
