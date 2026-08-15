# graph_builder.py - Builds and manages the knowledge graph.
"""
graph_builder.py
Coordinates entity/relation extraction and constructs the knowledge graph.

Handles:
- Entity deduplication via normalization + string matching
- Confidence threshold filtering
- Node/edge metadata enrichment (source URL, timestamp)
- Batch processing of multiple text chunks
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from app.knowledge_graph.entity_extractor import ExtractedEntity, get_entity_extractor
from app.knowledge_graph.graph_store import GraphEdge, GraphNode, get_graph_store
from app.knowledge_graph.relation_extractor import ExtractedRelation, get_relation_extractor
from app.core.config import settings

logger = logging.getLogger(__name__)

# Confidence thresholds
MIN_ENTITY_CONFIDENCE = 0.45
MIN_RELATION_CONFIDENCE = 0.50


def _normalize_id(name: str) -> str:
    """Convert entity name to a stable lowercase slug for use as a graph node ID."""
    return re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")


def _fuzzy_match(name_a: str, name_b: str) -> bool:
    """
    Simple fuzzy deduplication: True if names are very similar.
    Checks direct containment and shared significant token overlap.
    """
    a, b = name_a.lower(), name_b.lower()
    if a == b:
        return True
    if a in b or b in a:
        return True
    tokens_a = set(re.split(r"\W+", a)) - {"the", "a", "an", "of", "for", "and", ""}
    tokens_b = set(re.split(r"\W+", b)) - {"the", "a", "an", "of", "for", "and", ""}
    if not tokens_a or not tokens_b:
        return False
    overlap = len(tokens_a & tokens_b) / max(len(tokens_a), len(tokens_b))
    return overlap >= 0.75


class GraphBuilder:
    """
    Orchestrates entity + relation extraction and merges results
    into the persistent InMemoryGraphStore.
    """

    def __init__(self):
        self._entity_extractor = get_entity_extractor()
        self._relation_extractor = get_relation_extractor()
        self._store = get_graph_store()

    def process_chunk(
        self,
        text: str,
        source_url: str = "",
        source_title: str = "",
    ) -> Tuple[List[GraphNode], List[GraphEdge]]:
        """
        Extract entities and relations from a single text chunk,
        filter by confidence, deduplicate, and store in the graph.

        Returns:
            Tuple of (new_nodes, new_edges) that were added to the graph.
        """
        new_nodes: List[GraphNode] = []
        new_edges: List[GraphEdge] = []

        # 1. Entity extraction
        raw_entities = self._entity_extractor.extract_entities(text)
        filtered_entities = [
            e for e in raw_entities if e.confidence >= MIN_ENTITY_CONFIDENCE
        ]

        if not filtered_entities:
            logger.debug("[GraphBuilder] No qualifying entities found in chunk.")
            return [], []

        # 2. Deduplicate against existing graph nodes
        resolved_entities = self._deduplicate_entities(filtered_entities)

        # 3. Build GraphNode objects and add to store
        for entity in resolved_entities:
            node_id = _normalize_id(entity.name)
            node = GraphNode(
                id=node_id,
                name=entity.name,
                entity_type=entity.entity_type,
                description=entity.description,
                confidence=entity.confidence,
                aliases=entity.aliases,
                sources=[source_url] if source_url else [],
                created_at=time.time(),
                updated_at=time.time(),
            )
            is_new = self._store.add_node(node)
            if is_new:
                new_nodes.append(node)

        # 4. Relation extraction (using resolved entity names)
        entity_names = [e.name for e in resolved_entities]
        if len(entity_names) >= 2:
            raw_relations = self._relation_extractor.extract_relations(
                text, entity_names
            )
            filtered_relations = [
                r for r in raw_relations if r.confidence >= MIN_RELATION_CONFIDENCE
            ]

            # 5. Build GraphEdge objects and add to store
            for relation in filtered_relations:
                source_id = _normalize_id(relation.source)
                target_id = _normalize_id(relation.target)

                # Ensure both endpoints exist in graph
                if not self._store.get_node(source_id) or not self._store.get_node(target_id):
                    continue

                edge = GraphEdge(
                    source_id=source_id,
                    target_id=target_id,
                    relation_type=relation.relation_type,
                    description=relation.description,
                    confidence=relation.confidence,
                    created_at=time.time(),
                )
                is_new = self._store.add_edge(edge)
                if is_new:
                    new_edges.append(edge)

        logger.info(
            f"[GraphBuilder] Chunk processed: +{len(new_nodes)} nodes, "
            f"+{len(new_edges)} edges from '{source_title or source_url or 'unknown'}'"
        )
        return new_nodes, new_edges

    def process_chunks(
        self,
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Process a list of retrieved/extracted content chunks from the RAG pipeline.
        Each chunk dict should have 'content' (or 'text'), 'url', 'title' keys.

        Returns:
            Summary dict with total nodes and edges added.
        """
        total_nodes, total_edges = 0, 0
        limited_chunks = chunks[: settings.MAX_KG_CHUNKS]
        for chunk in limited_chunks:
            text = chunk.get("content") or chunk.get("text") or chunk.get("chunk_text", "")
            meta = chunk.get("metadata", chunk)
            url = meta.get("url", "")
            title = meta.get("title", "")
            if not text.strip():
                continue
            nodes, edges = self.process_chunk(text, source_url=url, source_title=title)
            total_nodes += len(nodes)
            total_edges += len(edges)

        # Persist after processing all chunks
        if total_nodes + total_edges > 0:
            self._store.save()

        return {"nodes_added": total_nodes, "edges_added": total_edges}

    def _deduplicate_entities(
        self, entities: List[ExtractedEntity]
    ) -> List[ExtractedEntity]:
        """
        Remove duplicate entities from the extraction result and resolve
        them against existing nodes in the graph.
        Prefers higher-confidence entities when duplicates exist.
        """
        deduped: List[ExtractedEntity] = []
        seen_names: List[str] = []

        # Collect existing node names from store for cross-session deduplication
        existing_names = [n.name for n in self._store.all_nodes()]

        for entity in entities:
            # Check against already-seen names in this batch
            is_dup = False
            for seen in seen_names:
                if _fuzzy_match(entity.name, seen):
                    is_dup = True
                    break

            # Check against existing graph nodes
            if not is_dup:
                for existing in existing_names:
                    if _fuzzy_match(entity.name, existing):
                        # Resolve to existing canonical name
                        entity.name = existing
                        is_dup = False   # Allow through but with canonical name
                        break

            if not is_dup:
                deduped.append(entity)
                seen_names.append(entity.name)

        return deduped

    def get_graph_snapshot(self) -> Dict[str, Any]:
        """Return the full graph as a serializable dict for API or WebSocket delivery."""
        return {
            "nodes": [n.to_dict() for n in self._store.all_nodes()],
            "edges": [e.to_dict() for e in self._store.all_edges()],
            "stats": self._store.stats(),
        }


# Module-level singleton
_graph_builder_instance: Optional[GraphBuilder] = None


def get_graph_builder() -> GraphBuilder:
    global _graph_builder_instance
    if _graph_builder_instance is None:
        _graph_builder_instance = GraphBuilder()
    return _graph_builder_instance
