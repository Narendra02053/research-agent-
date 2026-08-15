import logging
import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List

from app.services.search_service import SearchService
from app.services.extraction_service import ExtractionService
from app.services.indexing_service import IndexingService
from app.services.answer_service import AnswerService

# We'll need factory functions for dependency injection
def get_search_service() -> SearchService: return SearchService()
def get_extraction_service() -> ExtractionService: return ExtractionService()
def get_indexing_service() -> IndexingService: return IndexingService()
def get_answer_service() -> AnswerService: return AnswerService()

router = APIRouter(prefix="/deep-research", tags=["Deep Research"])
logger = logging.getLogger(__name__)

class DeepResearchRequest(BaseModel):
    query: str

class SourceItem(BaseModel):
    title: str
    url: str

class DeepResearchResponse(BaseModel):
    query: str
    answer: str
    sources: List[SourceItem]

@router.post("/", response_model=DeepResearchResponse)
async def perform_deep_research(
    request: DeepResearchRequest,
    search_service: SearchService = Depends(get_search_service),
    extraction_service: ExtractionService = Depends(get_extraction_service),
    indexing_service: IndexingService = Depends(get_indexing_service),
    answer_service: AnswerService = Depends(get_answer_service)
):
    """
    Final research endpoint combining all pipelines:
    Search -> Extraction -> Indexing -> Retrieval -> Reranking -> LLM context building
    """
    logger.info(f"Starting deep research for query: {request.query}")
    loop = asyncio.get_running_loop()
    
    try:
        # 1. Web Search
        search_results = await loop.run_in_executor(None, search_service.search_web, request.query)
        if not search_results:
            logger.warning("No search results found.")
            
        # 2. Extraction
        async def fetch_and_extract(result):
            content = await loop.run_in_executor(None, extraction_service.extract_webpage_content, result["url"])
            return {
                "title": result["title"], 
                "url": result["url"], 
                "content": content if content else result["content_snippet"]
            }
            
        tasks = [fetch_and_extract(res) for res in search_results]
        extracted_sources = await asyncio.gather(*tasks)
        
        # 3. Indexing
        if extracted_sources:
            await loop.run_in_executor(None, indexing_service.index_search_results, extracted_sources)
        
        # 4. Generate Answer (Retrieval -> Rerank -> Context -> LLM)
        answer_result = await loop.run_in_executor(None, answer_service.generate_research_answer, request.query)
        
        return DeepResearchResponse(
            query=request.query,
            answer=answer_result["answer"],
            sources=[SourceItem(**src) for src in answer_result["sources"]]
        )
        
    except Exception as e:
        logger.error(f"Deep research pipeline failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
