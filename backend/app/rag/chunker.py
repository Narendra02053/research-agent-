import uuid
import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class ContentChunker:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 150):
        """
        Initialize the RecursiveCharacterTextSplitter optimized for semantic meaning.
        It prioritizes splitting by paragraphs, then sentences, then words.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
    def chunk_content(self, text: str, title: str, url: str) -> List[Dict[str, Any]]:
        """
        Intelligently chunk content, preserve readable structure,
        and discard noisy/extremely small chunks.
        """
        if not text or not text.strip():
            return []
            
        # Split text into chunks
        chunks = self.text_splitter.split_text(text)
        processed_chunks = []
        
        for chunk in chunks:
            clean_chunk = chunk.strip()
            # Discard extremely small chunks which might be noise
            if len(clean_chunk) < 50:
                continue
                
            processed_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "source_title": title,
                "source_url": url,
                "chunk_text": clean_chunk
            })
            
        logger.info(f"Generated {len(processed_chunks)} valid chunks from {url}")
        return processed_chunks
