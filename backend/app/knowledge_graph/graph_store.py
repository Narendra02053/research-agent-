"""
graph_store.py
Thread-safe in-memory Knowledge Graph store with JSON persistence.

Provides an abstract BaseGraphStore interface designed for easy future
migration to Neo4j or Memgraph. The default InMemoryGraphStore supports:
- Thread-safe CRUD for nodes and edges
- Multi-hop BFS/DFS traversal
- Auto-save/load from JSON
"""

import json
import logging
import os
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# Default persistence path (relative to backend root)
_DEFAULT_GRAPH_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "research_memory_graph.json"
)


@dataclass
class GraphNode:
    """A node in the knowledge graph."""
    id: str                          # Normalized entity name (unique)
    name: str                        # Display name
    entity_type: str                 # e.g. company, person, technology
    description: str = ""
    confidence: float = 1.0
    aliases: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)   # Source URLs
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    mention_count: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GraphNode":
        return GraphNode(**{k: v for k, v in d.items() if k in GraphNode.__dataclass_fields__})


@dataclass
class GraphEdge:
    """A directed edge (relationship) in the knowledge graph."""
    source_id: str
    target_id: str
    relation_type: str
    description: str = ""
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    mention_count: int = 1

    @property
    def id(self) -> str:
        return f"{self.source_id}|{self.relation_type}|{self.target_id}"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["id"] = self.id
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GraphEdge":
        d.pop("id", None)
        return GraphEdge(**{k: v for k, v in d.items() if k in GraphEdge.__dataclass_fields__})


class BaseGraphStore(ABC):
    """Abstract interface for knowledge graph backends."""

    @abstractmethod
    def add_node(self, node: GraphNode) -> bool:
        """Add or merge a node. Returns True if new, False if merged."""

    @abstractmethod
    def add_edge(self, edge: GraphEdge) -> bool:
        """Add or merge an edge. Returns True if new, False if merged."""

    @abstractmethod
    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve a node by id."""

    @abstractmethod
    def get_neighbors(self, node_id: str, max_hops: int = 1) -> Dict[str, Any]:
        """Get neighbor nodes and connecting edges up to max_hops depth."""

    @abstractmethod
    def all_nodes(self) -> List[GraphNode]:
        """Return all nodes in the graph."""

    @abstractmethod
    def all_edges(self) -> List[GraphEdge]:
        """Return all edges in the graph."""

    @abstractmethod
    def search_nodes(self, query: str, top_k: int = 10) -> List[GraphNode]:
        """Keyword search across node names, aliases, and descriptions."""

    @abstractmethod
    def clear(self):
        """Remove all nodes and edges from the graph."""

    @abstractmethod
    def stats(self) -> Dict[str, int]:
        """Return basic graph statistics."""


class InMemoryGraphStore(BaseGraphStore):
    """
    Thread-safe in-memory knowledge graph with JSON persistence.
    Nodes are keyed by normalized entity name (node id).
    Edges are keyed by 'source|relation|target'.
    """

    def __init__(self, persistence_path: Optional[str] = None):
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}
        # Adjacency: source_id -> set of edge ids
        self._adj_out: Dict[str, Set[str]] = defaultdict(set)
        # Reverse adjacency: target_id -> set of edge ids
        self._adj_in: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()
        self._persistence_path = persistence_path or _DEFAULT_GRAPH_PATH
        self._load()

    # ------------------------------------------------------------------ #
    #  Node Operations                                                     #
    # ------------------------------------------------------------------ #
    def add_node(self, node: GraphNode) -> bool:
        with self._lock:
            if node.id in self._nodes:
                existing = self._nodes[node.id]
                # Merge: update description if better confidence, increment count
                if node.confidence > existing.confidence:
                    existing.description = node.description
                    existing.confidence = node.confidence
                existing.mention_count += 1
                existing.updated_at = time.time()
                # Merge aliases and sources
                existing.aliases = list(set(existing.aliases + node.aliases))
                existing.sources = list(set(existing.sources + node.sources))[:20]
                return False
            else:
                self._nodes[node.id] = node
                logger.debug(f"[KG] Node added: {node.id} ({node.entity_type})")
                return True

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        with self._lock:
            return self._nodes.get(node_id)

    # ------------------------------------------------------------------ #
    #  Edge Operations                                                     #
    # ------------------------------------------------------------------ #
    def add_edge(self, edge: GraphEdge) -> bool:
        with self._lock:
            if edge.id in self._edges:
                existing = self._edges[edge.id]
                if edge.confidence > existing.confidence:
                    existing.description = edge.description
                    existing.confidence = edge.confidence
                existing.mention_count += 1
                return False
            else:
                self._edges[edge.id] = edge
                self._adj_out[edge.source_id].add(edge.id)
                self._adj_in[edge.target_id].add(edge.id)
                logger.debug(f"[KG] Edge added: {edge.id}")
                return True

    # ------------------------------------------------------------------ #
    #  Graph Traversal                                                     #
    # ------------------------------------------------------------------ #
    def get_neighbors(
        self, node_id: str, max_hops: int = 1
    ) -> Dict[str, Any]:
        """
        BFS traversal up to max_hops from node_id.
        Returns {'nodes': [...], 'edges': [...]} sub-graph dict.
        """
        with self._lock:
            visited_nodes: Set[str] = set()
            result_nodes: List[GraphNode] = []
            result_edges: List[GraphEdge] = []
            queue: deque = deque([(node_id, 0)])

            while queue:
                current_id, depth = queue.popleft()
                if current_id in visited_nodes:
                    continue
                visited_nodes.add(current_id)

                if current_id in self._nodes:
                    result_nodes.append(self._nodes[current_id])

                if depth >= max_hops:
                    continue

                # Outgoing edges
                for edge_id in self._adj_out.get(current_id, set()):
                    edge = self._edges.get(edge_id)
                    if edge and edge_id not in {e.id for e in result_edges}:
                        result_edges.append(edge)
                        if edge.target_id not in visited_nodes:
                            queue.append((edge.target_id, depth + 1))

                # Incoming edges
                for edge_id in self._adj_in.get(current_id, set()):
                    edge = self._edges.get(edge_id)
                    if edge and edge_id not in {e.id for e in result_edges}:
                        result_edges.append(edge)
                        if edge.source_id not in visited_nodes:
                            queue.append((edge.source_id, depth + 1))

            return {
                "nodes": [n.to_dict() for n in result_nodes],
                "edges": [e.to_dict() for e in result_edges],
            }

    def search_nodes(self, query: str, top_k: int = 10) -> List[GraphNode]:
        """Case-insensitive keyword search across name, aliases, and description."""
        with self._lock:
            q = query.lower()
            scored: List[Tuple[float, GraphNode]] = []
            for node in self._nodes.values():
                score = 0.0
                if q in node.name.lower():
                    score += 2.0
                if any(q in alias.lower() for alias in node.aliases):
                    score += 1.5
                if q in node.description.lower():
                    score += 0.5
                if score > 0:
                    scored.append((score + node.mention_count * 0.1, node))

            scored.sort(key=lambda x: x[0], reverse=True)
            return [n for _, n in scored[:top_k]]

    def all_nodes(self) -> List[GraphNode]:
        with self._lock:
            return list(self._nodes.values())

    def all_edges(self) -> List[GraphEdge]:
        with self._lock:
            return list(self._edges.values())

    def clear(self):
        with self._lock:
            self._nodes.clear()
            self._edges.clear()
            self._adj_out.clear()
            self._adj_in.clear()
        logger.info("[KG] Graph cleared.")

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
            }

    # ------------------------------------------------------------------ #
    #  Persistence                                                         #
    # ------------------------------------------------------------------ #
    def save(self):
        """Persist the graph to JSON."""
        os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
        with self._lock:
            payload = {
                "nodes": [n.to_dict() for n in self._nodes.values()],
                "edges": [e.to_dict() for e in self._edges.values()],
                "saved_at": time.time(),
            }
        try:
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            logger.info(f"[KG] Graph saved: {len(payload['nodes'])} nodes, {len(payload['edges'])} edges.")
        except Exception as e:
            logger.error(f"[KG] Failed to save graph: {e}")

    def _load(self):
        """Load the graph from JSON if it exists."""
        if not os.path.exists(self._persistence_path):
            logger.info("[KG] No persisted graph found. Starting fresh.")
            return
        try:
            with open(self._persistence_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            for nd in payload.get("nodes", []):
                node = GraphNode.from_dict(nd)
                self._nodes[node.id] = node
            for ed in payload.get("edges", []):
                edge = GraphEdge.from_dict(ed)
                self._edges[edge.id] = edge
                self._adj_out[edge.source_id].add(edge.id)
                self._adj_in[edge.target_id].add(edge.id)
            logger.info(
                f"[KG] Loaded graph: {len(self._nodes)} nodes, {len(self._edges)} edges "
                f"from {self._persistence_path}"
            )
        except Exception as e:
            logger.error(f"[KG] Failed to load graph: {e}")


# ------------------------------------------------------------------ #
#  Module-level singleton                                              #
# ------------------------------------------------------------------ #
_graph_store_instance: Optional[InMemoryGraphStore] = None


def get_graph_store() -> InMemoryGraphStore:
    global _graph_store_instance
    if _graph_store_instance is None:
        _graph_store_instance = InMemoryGraphStore()
    return _graph_store_instance
