import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.evaluation.source_validator import SourceValidator
from app.evaluation.answer_scorer import AnswerScorer
from app.evaluation.relevance_evaluator import RelevanceEvaluator
from app.evaluation.hallucination_checker import HallucinationChecker
from app.evaluation.research_quality import ResearchQualityPipeline

def test_source_validator_detailed():
    sources = [
        {
            "url": "https://nature.com/article123",
            "pub_date": "2025-06-01",
            "citation_count": 12
        },
        {
            "url": "http://random-blog.blogspot.com/post",
            "pub_date": "2020-01-01",
            "citation_count": 0
        }
    ]
    result = SourceValidator.evaluate_sources(sources)
    
    assert result["source_quality"] > 0
    assert len(result["details"]) == 2
    
    high_trust = result["details"][0]
    low_trust = result["details"][1]
    
    assert high_trust["https_valid"] is True
    assert high_trust["domain_authority"] == 1.0
    assert high_trust["freshness_score"] == 1.0 # 2026 - 2025 = 1 year
    assert high_trust["is_organization_or_research"] is True
    assert high_trust["citation_count"] == 12
    assert high_trust["trust_score"] > 0.8
    
    assert low_trust["https_valid"] is False # http
    assert low_trust["domain_authority"] == 0.2
    assert low_trust["freshness_score"] == 0.4 # 2026 - 2020 = 6 years old
    assert low_trust["is_organization_or_research"] is False
    assert low_trust["citation_count"] == 0
    assert low_trust["trust_score"] < 0.4

def test_relevance_evaluator_embeddings():
    mock_emb_svc = MagicMock()
    mock_emb_svc.embed_text.return_value = [0.1] * 128
    mock_emb_svc.embed_documents.return_value = [[0.1] * 128, [0.2] * 128]
    
    retrieved = [
        {"content": "Chunk one content"},
        {"text": "Chunk two text"}
    ]
    reranked = [
        {"content": "Chunk one content", "score": 0.9},
        {"text": "Chunk two text", "score": 0.8}
    ]
    
    with patch("app.evaluation.relevance_evaluator.get_embedding_service", return_value=mock_emb_svc):
        result = RelevanceEvaluator.evaluate_retrieval(
            query="test query",
            retrieved_chunks=retrieved,
            reranked_chunks=reranked
        )
        
    assert result["chunks_analyzed"] == 2
    assert result["average_similarity"] == 1.0 # Identical direction vectors
    assert result["retrieval_precision"] == 1.0 # similarity 1.0 >= 0.6
    # 70% * 1.0 + 30% * 0.85 = 0.955 -> rounded to 0.95
    assert result["retrieval_quality"] == 0.95
    assert result["confidence"] == "High"

@patch("app.evaluation.answer_scorer.get_llm_service")
def test_answer_scorer_llm(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = """
    ```json
    {
      "completeness": 0.95,
      "accuracy": 0.90,
      "clarity": 0.95,
      "evidence_usage": 0.90,
      "citation_quality": 0.85,
      "answer_quality": 0.92
    }
    ```
    """
    mock_get_llm.return_value = mock_llm
    
    result = AnswerScorer.score_answer("report", "query", "context")
    
    assert result["completeness"] == 0.95
    assert result["accuracy"] == 0.90
    assert result["clarity"] == 0.95
    assert result["evidence_usage"] == 0.90
    assert result["citation_quality"] == 0.85
    assert result["answer_quality"] == 0.92

@patch("app.evaluation.answer_scorer.get_llm_service")
def test_answer_scorer_fallback(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.generate_response.side_effect = Exception("LLM connection failed")
    mock_get_llm.return_value = mock_llm
    
    result = AnswerScorer.score_answer("report text", "query")
    assert "answer_quality" in result
    assert result["answer_quality"] > 0.0

@patch("app.evaluation.hallucination_checker.get_llm_service")
def test_hallucination_checker_llm(mock_get_llm):
    mock_llm = MagicMock()
    mock_llm.generate_response.return_value = """
    {
      "hallucination_risk": 0.10,
      "grounding_score": 0.90,
      "unsupported_claims": ["claim A"],
      "supported_claims": ["claim B", "claim C"]
    }
    """
    mock_get_llm.return_value = mock_llm
    
    result = HallucinationChecker.check_hallucinations("query", "context", "report")
    
    assert result["hallucination_risk"] == 0.10
    assert result["grounding_score"] == 0.90
    assert "claim A" in result["unsupported_claims"]
    assert "claim B" in result["supported_claims"]

@patch("app.evaluation.answer_scorer.get_llm_service")
@patch("app.evaluation.hallucination_checker.get_llm_service")
def test_research_quality_pipeline(mock_get_hallucination_llm, mock_get_answer_llm):
    # Mock LLM for Hallucination Checker
    mock_hallucination_llm = MagicMock()
    mock_hallucination_llm.generate_response.return_value = """
    {
      "hallucination_risk": 0.20,
      "grounding_score": 0.80,
      "unsupported_claims": ["claim 1"],
      "supported_claims": ["claim 2", "claim 3", "claim 4"]
    }
    """
    mock_get_hallucination_llm.return_value = mock_hallucination_llm
    
    # Mock LLM for Answer Scorer
    mock_answer_llm = MagicMock()
    mock_answer_llm.generate_response.return_value = """
    {
      "completeness": 0.90,
      "accuracy": 0.90,
      "clarity": 0.90,
      "evidence_usage": 0.80,
      "citation_quality": 0.80,
      "answer_quality": 0.85
    }
    """
    mock_get_answer_llm.return_value = mock_answer_llm
    
    # Mock Embeddings for Relevance Evaluator
    mock_emb_svc = MagicMock()
    mock_emb_svc.embed_text.return_value = [0.1] * 128
    mock_emb_svc.embed_documents.return_value = [[0.1] * 128, [0.1] * 128]
    
    state = {
        "query": "query",
        "sources": [{"url": "https://nature.com", "pub_date": "2025-06-01", "citation_count": 10}],
        "retrieved_chunks": [{"content": "chunk 1"}, {"content": "chunk 2"}],
        "reranked_chunks": [{"content": "chunk 1", "score": 0.9}, {"content": "chunk 2", "score": 0.9}],
        "context": "context",
        "final_answer": "final report"
    }
    
    with patch("app.evaluation.relevance_evaluator.get_embedding_service", return_value=mock_emb_svc):
        result = ResearchQualityPipeline.evaluate_research(state)
        
    assert result["source_quality"] > 0
    assert result["retrieval_quality"] == 0.97  # 70% * 1.0 similarity + 30% * 0.9 reranker
    assert result["retrieval_precision"] == 1.0
    assert result["grounding_score"] == 0.8
    assert result["hallucination_risk"] == 0.2
    assert result["citation_coverage"] == 0.75  # 3 supported / 4 total
    assert result["answer_quality"] == 0.85
    
    # Weighting check:
    # Grounding: 0.8 * 0.3 = 0.24
    # Answer Quality: 0.85 * 0.2 = 0.17
    # Retrieval Quality: 0.97 * 0.2 = 0.194
    # Source Quality: 1.0 * 0.1 = 0.10 (source has https, high trust, fresh, org, citation count)
    # Citation Coverage: 0.75 * 0.2 = 0.15
    # Total = 0.24 + 0.17 + 0.194 + 0.10 + 0.15 = 0.854 -> rounds to 0.85
    assert result["overall_confidence"] == 0.85
