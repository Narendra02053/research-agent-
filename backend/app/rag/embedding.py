import logging
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Singleton-style initialization for HuggingFace embeddings.
    Optimized for reusability and fast startup in production.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            logger.info("Initializing HuggingFace Embedding model: BAAI/bge-small-en-v1.5")
            cls._instance = super(EmbeddingService, cls).__new__(cls)
            
            # Initialize model (cpu is explicitly defined for local dev, can scale to cuda in production)
            model_kwargs = {'device': 'cpu'}
            # Normalize embeddings for cosine similarity
            encode_kwargs = {'normalize_embeddings': True}
            
            cls._instance.embeddings = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5",
                model_kwargs=model_kwargs,
                encode_kwargs=encode_kwargs
            )
        return cls._instance

    def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text."""
        return self.embeddings.embed_query(text)
        
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        return self.embeddings.embed_documents(texts)
        
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
