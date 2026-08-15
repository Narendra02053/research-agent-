# rag_instrumentation.py - Instrumentation for RAG tracing.
"""
rag_instrumentation.py
─────────────────────────────────────────────────────────────────
Phoenix / OTEL spans for the custom RAG pipeline steps that are
NOT automatically covered by the LangChain instrumentor:

  • Embedding generation  (HuggingFace sentence-transformers)
  • Qdrant vector retrieval
  • Cross-encoder reranking (BAAI/bge-reranker-base)
  • Knowledge Graph ingestion + query

Each function returns a context-manager decorator so it can wrap
the actual service methods without modifying their signatures.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────
# Embedding span
# ─────────────────────────────────────────────────────────────────
def trace_embedding(texts: List[str], model_name: str = "BAAI/bge-small-en-v1.5") -> "EmbeddingSpan":
    """
    Usage:
        with trace_embedding(texts) as span:
            embeddings = service.embed_documents(texts)
            span.finish(len(embeddings))
    """
    from app.observability.phoenix_tracer import phoenix_span
    return _EmbeddingSpan(texts=texts, model_name=model_name)


class _EmbeddingSpan:
    def __init__(self, texts: List[str], model_name: str):
        self._texts = texts
        self._model = model_name
        self._span_ctx = None
        self._span = None

    def __enter__(self):
        from app.observability.phoenix_tracer import phoenix_span
        attrs = {
            "embedding.model": self._model,
            "embedding.input_count": len(self._texts),
            "embedding.total_chars": sum(len(t) for t in self._texts),
        }
        self._span_ctx = phoenix_span("embedding.generate", attrs, span_kind="RETRIEVER")
        self._span = self._span_ctx.__enter__()
        return self

    def finish(self, vector_count: int):
        if self._span:
            self._span.set_attribute("embedding.output_vectors", vector_count)

    def __exit__(self, *args):
        if self._span_ctx:
            self._span_ctx.__exit__(*args)


# ─────────────────────────────────────────────────────────────────
# Qdrant retrieval span
# ─────────────────────────────────────────────────────────────────
class VectorRetrievalSpan:
    """
    Context manager wrapping a Qdrant semantic search call.

    Usage:
        with VectorRetrievalSpan(query=q, collection="docs", limit=10) as span:
            results = qdrant_client.search(...)
            span.finish(results)
    """

    def __init__(self, query: str, collection: str, limit: int):
        self._query = query
        self._collection = collection
        self._limit = limit
        self._span_ctx = None
        self._span = None
        self._t0 = 0.0

    def __enter__(self):
        from app.observability.phoenix_tracer import phoenix_span
        attrs = {
            "retrieval.query": self._query[:300],
            "retrieval.collection": self._collection,
            "retrieval.limit": self._limit,
        }
        self._span_ctx = phoenix_span("qdrant.search", attrs, span_kind="RETRIEVER")
        self._span = self._span_ctx.__enter__()
        self._t0 = time.perf_counter()
        return self

    def finish(self, results: List[Dict]):
        elapsed_ms = (time.perf_counter() - self._t0) * 1000
        if self._span:
            self._span.set_attribute("retrieval.result_count", len(results))
            self._span.set_attribute("retrieval.latency_ms", round(elapsed_ms, 1))
            if results:
                top_score = results[0].get("score", 0.0) if isinstance(results[0], dict) else 0.0
                self._span.set_attribute("retrieval.top_score", round(top_score, 4))

    def __exit__(self, *args):
        if self._span_ctx:
            self._span_ctx.__exit__(*args)


# ─────────────────────────────────────────────────────────────────
# Cross-encoder reranker span
# ─────────────────────────────────────────────────────────────────
class RerankerSpan:
    """
    Context manager wrapping a cross-encoder reranking call.

    Usage:
        with RerankerSpan(query=q, input_count=len(chunks)) as span:
            reranked = reranker.predict(pairs)
            span.finish(top_k_count=5)
    """

    def __init__(self, query: str, input_count: int, model: str = "BAAI/bge-reranker-base"):
        self._query = query
        self._input_count = input_count
        self._model = model
        self._span_ctx = None
        self._span = None
        self._t0 = 0.0

    def __enter__(self):
        from app.observability.phoenix_tracer import phoenix_span
        attrs = {
            "reranker.query": self._query[:200],
            "reranker.model": self._model,
            "reranker.input_chunks": self._input_count,
        }
        self._span_ctx = phoenix_span("reranker.score", attrs, span_kind="RERANKER")
        self._span = self._span_ctx.__enter__()
        self._t0 = time.perf_counter()
        return self

    def finish(self, top_k_count: int):
        elapsed_ms = (time.perf_counter() - self._t0) * 1000
        if self._span:
            self._span.set_attribute("reranker.output_chunks", top_k_count)
            self._span.set_attribute("reranker.latency_ms", round(elapsed_ms, 1))

    def __exit__(self, *args):
        if self._span_ctx:
            self._span_ctx.__exit__(*args)


# ─────────────────────────────────────────────────────────────────
# Knowledge Graph instrumentation
# ─────────────────────────────────────────────────────────────────
class KGIngestSpan:
    """Wraps knowledge graph chunk ingestion."""

    def __init__(self, chunk_count: int, query: str = ""):
        self._chunk_count = chunk_count
        self._query = query
        self._span_ctx = None
        self._span = None

    def __enter__(self):
        from app.observability.phoenix_tracer import phoenix_span
        attrs = {
            "kg.input_chunks": self._chunk_count,
            "kg.query": self._query[:200],
        }
        self._span_ctx = phoenix_span("knowledge_graph.ingest", attrs, span_kind="CHAIN")
        self._span = self._span_ctx.__enter__()
        return self

    def finish(self, nodes_added: int, edges_added: int, total_nodes: int, total_edges: int):
        if self._span:
            self._span.set_attribute("kg.nodes_added", nodes_added)
            self._span.set_attribute("kg.edges_added", edges_added)
            self._span.set_attribute("kg.total_nodes", total_nodes)
            self._span.set_attribute("kg.total_edges", total_edges)

    def __exit__(self, *args):
        if self._span_ctx:
            self._span_ctx.__exit__(*args)


class KGQuerySpan:
    """Wraps knowledge graph context retrieval for LLM synthesis."""

    def __init__(self, query: str, max_hops: int = 2):
        self._query = query
        self._max_hops = max_hops
        self._span_ctx = None
        self._span = None

    def __enter__(self):
        from app.observability.phoenix_tracer import phoenix_span
        attrs = {
            "kg.query": self._query[:200],
            "kg.max_hops": self._max_hops,
        }
        self._span_ctx = phoenix_span("knowledge_graph.query", attrs, span_kind="RETRIEVER")
        self._span = self._span_ctx.__enter__()
        return self

    def finish(self, nodes_in_context: int, edges_in_context: int, context_chars: int):
        if self._span:
            self._span.set_attribute("kg.context_nodes", nodes_in_context)
            self._span.set_attribute("kg.context_edges", edges_in_context)
            self._span.set_attribute("kg.context_chars", context_chars)

    def __exit__(self, *args):
        if self._span_ctx:
            self._span_ctx.__exit__(*args)
