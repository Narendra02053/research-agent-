import pytest
from app.evaluation.source_validator import SourceValidator
from app.evaluation.answer_scorer import AnswerScorer
from app.evaluation.relevance_evaluator import RelevanceEvaluator

def test_source_validator():
    sources = [
        {"url": "https://nature.com/article123"},
        {"url": "https://random-blog.blogspot.com/post"}
    ]
    result = SourceValidator.evaluate_sources(sources)
    assert result["source_quality"] > 0
    assert len(result["details"]) == 2
    assert result["details"][0]["trust_score"] > result["details"][1]["trust_score"]

def test_answer_scorer():
    report = "## Key Findings\n\nThis is a solid report. Source: https://example.com"
    result = AnswerScorer.score_answer(report, "test query")
    assert result["answer_quality"] > 0.5
    assert result["length"] == len(report)

def test_relevance_evaluator_no_chunks():
    result = RelevanceEvaluator.evaluate_retrieval("query", [], [])
    assert result["retrieval_quality"] == 0.0
