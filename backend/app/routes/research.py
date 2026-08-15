# research.py - Standard API endpoints for research.
import logging
import asyncio
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.services.search_service import SearchService
from app.services.extraction_service import ExtractionService
from app.services.indexing_service import IndexingService

# Initialize router and logger
router = APIRouter(prefix="/research", tags=["Research"])
logger = logging.getLogger(__name__)

# Request Model
class ResearchRequest(BaseModel):
    query: str

# Response Models
class SourceResult(BaseModel):
    title: str
    url: str
    content: str

class ResearchResponse(BaseModel):
    query: str
    sources: List[SourceResult]

# Dependency injection for services
def get_search_service() -> SearchService:
    return SearchService()

def get_extraction_service() -> ExtractionService:
    return ExtractionService()

def get_indexing_service() -> IndexingService:
    return IndexingService()

@router.post("/", response_model=ResearchResponse)
async def perform_research(
    request: ResearchRequest,
    search_service: SearchService = Depends(get_search_service),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    indexing_service: IndexingService = Depends(get_indexing_service)
):
    """
    Perform internet research based on the provided query.
    1. Search the web using Tavily.
    2. Extract clean content from the top search results using Trafilatura.
    """
    logger.info(f"Received research request for query: {request.query}")
    
    try:
        # Run synchronous web search in an executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        search_results = await loop.run_in_executor(
            None, search_service.search_web, request.query
        )
        
        # Extract content from search results concurrently
        async def fetch_and_extract(result: dict) -> SourceResult:
            content = await loop.run_in_executor(
                None, extraction_service.extract_webpage_content, result["url"]
            )
            
            # Fallback to the search result snippet if extraction fails
            final_content = content if content else result["content_snippet"]
            
            return SourceResult(
                title=result["title"],
                url=result["url"],
                content=final_content
            )
            
        tasks = [fetch_and_extract(res) for res in search_results]
        sources = await asyncio.gather(*tasks)
        
        # 3. Index the extracted search results into Qdrant vector database
        try:
            results_to_index = [{"title": s.title, "url": s.url, "content": s.content} for s in sources]
            await loop.run_in_executor(None, indexing_service.index_search_results, results_to_index)
        except Exception as idx_err:
            logger.error(f"Indexing failed, but returning research results. Error: {str(idx_err)}")
        
        return ResearchResponse(
            query=request.query,
            sources=sources
        )

    except Exception as e:
        logger.error(f"Research pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
