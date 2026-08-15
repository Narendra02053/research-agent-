import logging
import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.rag.vector_store import VectorStoreService, get_vector_store

router = APIRouter(prefix="/search", tags=["Search"])
logger = logging.getLogger(__name__)

# Request Model
class SearchRequest(BaseModel):
    query: str

# Response Models
class Metadata(BaseModel):
    title: str
    url: str

class SearchResult(BaseModel):
    content: str
    score: float
    metadata: Metadata

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]

@router.post("/", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    vector_store: VectorStoreService = Depends(get_vector_store)
):
    """
    Perform semantic search over indexed knowledge in the vector database.
    """
    logger.info(f"Received semantic search request for query: {request.query}")
    try:
        loop = asyncio.get_running_loop()
        
        # Run Qdrant search in an executor
        raw_results = await loop.run_in_executor(
            None, vector_store.search_similar_content, request.query
        )
        
        formatted_results = []
        for r in raw_results:
            formatted_results.append(
                SearchResult(
                    content=r["content"],
                    score=r["score"],
                    metadata=Metadata(
                        title=r["metadata"].get("title", ""),
                        url=r["metadata"].get("url", "")
                    )
                )
            )
            
        return SearchResponse(
            query=request.query,
            results=formatted_results
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
