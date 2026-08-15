import logging
from typing import List, Dict, Any
from app.rag.chunker import ContentChunker
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

class IndexingService:
    def __init__(self):
        self.chunker = ContentChunker()
        self.vector_store = get_vector_store()
        
    def index_search_results(self, search_results: List[Dict[str, Any]]):
        """
        Receives extracted webpages, cleans content, chunks it,
        generates embeddings, and stores them in Qdrant.
        """
        try:
            all_chunks = []
            
            # Clean and Chunk content
            for result in search_results:
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                content = result.get("content", "")
                
                clean_content = content.strip() if content else ""
                if not clean_content:
                    continue
                    
                chunks = self.chunker.chunk_content(text=clean_content, title=title, url=url)
                all_chunks.extend(chunks)
                
            # Store Vectors
            if all_chunks:
                logger.info(f"Indexing {len(all_chunks)} total chunks into vector store.")
                self.vector_store.store_chunks(all_chunks)
            else:
                logger.warning("No chunks generated for indexing.")
                
        except Exception as e:
            logger.error(f"Error during indexing pipeline: {str(e)}")
            raise e
