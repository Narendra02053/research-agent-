import os
import time
import logging
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

from app.rag.embedding import get_embedding_service

logger = logging.getLogger(__name__)

class VectorStoreService:
    def __init__(self, collection_name: str = "deep_research_knowledge"):
        self.collection_name = collection_name
        self.embedding_service = get_embedding_service()
        
        # Local Qdrant instance
        qdrant_path = os.path.join(os.path.dirname(__file__), "..", "..", "qdrant_data")
        os.makedirs(qdrant_path, exist_ok=True)
        
        self.client = QdrantClient(path=qdrant_path)
        self._ensure_collection()
        
    def _ensure_collection(self):
        """Creates the collection if it does not exist using Cosine similarity."""
        collections = self.client.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            # bge-small-en-v1.5 has an embedding size of 384
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE),
            )
        else:
            logger.info(f"Qdrant Collection {self.collection_name} already exists.")
            
    def store_chunks(self, chunks: List[Dict[str, Any]]):
        """Stores vectors with metadata into Qdrant."""
        if not chunks:
            return
            
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
                "text": chunk["chunk_text"] # Payload holds text for retrieval
            }
            
            points.append(
                PointStruct(
                    id=chunk["chunk_id"], 
                    vector=embeddings[idx], 
                    payload=metadata
                )
            )
            
        logger.info(f"Upserting {len(points)} points into Qdrant collection: {self.collection_name}")
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        logger.info("Upsert complete.")

    def search_similar_content(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic similarity search in Qdrant based on the query."""
        logger.info(f"Performing semantic search for query: {query}")
        
        # Generate query embedding
        query_vector = self.embedding_service.embed_text(query)
        
        # Execute search
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            limit=limit
        )
        
        # Format results
        results = []
        for hit in search_result:
            results.append({
                "content": hit.payload.get("text", ""),
                "score": hit.score,
                "metadata": {
                    "title": hit.payload.get("title", ""),
                    "url": hit.payload.get("url", ""),
                    "chunk_id": hit.payload.get("chunk_id", ""),
                    "timestamp": hit.payload.get("timestamp", "")
                }
            })
            
        return results

def get_vector_store() -> VectorStoreService:
    return VectorStoreService()
