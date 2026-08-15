# vector_store.py - Vector database interface (e.g., Qdrant).
import time
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.rag.embedding import get_embedding_service
from app.core.config import settings

logger = logging.getLogger(__name__)

_vector_store_instance: Optional["VectorStoreService"] = None


class VectorStoreService:
    def __init__(self, collection_name: str = "deep_research_knowledge"):
        self.collection_name = collection_name
        self.embedding_service = get_embedding_service()
        self._client = None
        self._collection_ensured = False

    @property
    def client(self):
        if self._client is None:
            host = settings.QDRANT_HOST
            port = settings.QDRANT_PORT
            try:
                # Attempt to connect to external Qdrant and test connection
                client = QdrantClient(host=host, port=port, timeout=2.0)
                client.get_collections()
                self._client = client
                logger.info(f"Connected to Qdrant at {host}:{port}")
            except Exception as e:
                logger.warning(
                    f"External Qdrant at {host}:{port} is unavailable ({e}). "
                    "Falling back to in-memory Qdrant client (location=':memory:')."
                )
                self._client = QdrantClient(location=":memory:")
        return self._client


    def _ensure_collection(self):
        """Creates the collection if it does not exist using Cosine similarity."""
        if self._collection_ensured:
            return
        try:
            collections = self.client.get_collections().collections
            if not any(c.name == self.collection_name for c in collections):
                logger.info(f"Creating Qdrant collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
            else:
                logger.info(f"Qdrant Collection {self.collection_name} already exists.")
            self._collection_ensured = True
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            raise e

    def store_chunks(self, chunks: List[Dict[str, Any]]):
        """Stores vectors with metadata into Qdrant."""
        if not chunks:
            return
        
        self._ensure_collection()

        texts = [chunk["chunk_text"] for chunk in chunks]
        logger.info(f"Generating embeddings for {len(texts)} chunks...")
        embeddings = self.embedding_service.embed_documents(texts)

        points = []
        timestamp = time.time()

        for idx, chunk in enumerate(chunks):
            metadata = {
                "title": chunk["source_title"],
                "url": chunk["source_url"],
                "chunk_id": chunk["chunk_id"],
                "source_type": "webpage",
                "timestamp": timestamp,
                "text": chunk["chunk_text"],
            }

            points.append(
                PointStruct(
                    id=chunk["chunk_id"],
                    vector=embeddings[idx],
                    payload=metadata,
                )
            )

        logger.info(f"Upserting {len(points)} points into Qdrant collection: {self.collection_name}")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        logger.info("Upsert complete.")

    def search_similar_content(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic similarity search in Qdrant based on the query."""
        logger.info(f"Performing semantic search for query: {query}")
        
        self._ensure_collection()

        query_vector = self.embedding_service.embed_text(query)

        from app.observability.rag_instrumentation import VectorRetrievalSpan
        with VectorRetrievalSpan(query=query, collection=self.collection_name, limit=limit) as span:
            search_result = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
            )

            results = []
            for hit in search_result.points:
                results.append({
                    "content": hit.payload.get("text", ""),
                    "score": hit.score,
                    "metadata": {
                        "title": hit.payload.get("title", ""),
                        "url": hit.payload.get("url", ""),
                        "chunk_id": hit.payload.get("chunk_id", ""),
                        "timestamp": hit.payload.get("timestamp", ""),
                    },
                })
            span.finish(results)

        return results


def get_vector_store() -> VectorStoreService:
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStoreService()
    return _vector_store_instance
