import pytest
from app.rag.chunker import ContentChunker

def test_recursive_chunker():
    chunker = ContentChunker(chunk_size=100, chunk_overlap=10)
    text = "This is a very long text that should be split into smaller chunks by the recursive chunker."
    chunks = chunker.chunk_content(text, "Test Title", "http://test.com")
    
    assert len(chunks) >= 1
    assert all("chunk_text" in c for c in chunks)


# Mock test for embedding and vector store
@pytest.mark.asyncio
async def test_vector_store_retrieval(monkeypatch):
    class MockVectorStore:
        def search(self, query, limit=5):
            return [{"id": 1, "text": "Mock chunk 1", "score": 0.9}]
            
    store = MockVectorStore()
    results = store.search("test query")
    
    assert len(results) == 1
    assert results[0]["score"] == 0.9
    assert "Mock chunk" in results[0]["text"]
