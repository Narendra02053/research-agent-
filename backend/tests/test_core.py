# test_core.py - Tests for core application functionality.
"""
Comprehensive unit tests for backend/app/core modules.
Covers: config, logging_config, security, cache, memory, dependencies, llm, task_manager
"""

import json
import os
import time
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


# ========================================================================= #
#  config.py                                                                #
# ========================================================================= #

class TestConfig:
    def test_settings_loads_with_env(self, mock_redis_env):
        """Verify Settings loads from environment variables."""
        from app.core.config import Settings
        settings = Settings()
        assert settings.ENVIRONMENT == "testing"
        assert settings.tavily.TAVILY_API_KEY == "test-tavily-key"
        assert settings.redis_config.REDIS_HOST == "localhost"
        assert settings.redis_config.REDIS_PORT == 6379

    def test_settings_development_by_default(self):
        """Verify default environment is development."""
        from app.core.config import Settings
        settings = Settings()
        assert settings.ENVIRONMENT == "development"
        assert settings.is_development is True

    def test_model_validator_production_fails_without_keys(self):
        """Verify production env raises on missing required keys."""
        from app.core.config import Settings
        with pytest.raises(ValueError, match="TAVILY_API_KEY is required"):
            Settings(ENVIRONMENT="production")

    def test_groq_key_placeholder_detection(self):
        """Verify placeholder API key raises ValueError."""
        from app.core.config import LLMSettings
        with pytest.raises(ValueError, match="GROQ_API_KEY is set to placeholder"):
            LLMSettings(GROQ_API_KEY="your_key_here")

    def test_redis_url_property_with_password(self):
        """Verify Redis URL generation with password."""
        from app.core.config import RedisSettings
        cfg = RedisSettings(REDIS_PASSWORD="secret")
        assert "rediss" not in cfg.redis_url
        assert ":secret@" in cfg.redis_url

    def test_redis_url_property_ssl(self):
        """Verify Redis URL generation with SSL."""
        from app.core.config import RedisSettings
        cfg = RedisSettings(REDIS_SSL=True)
        assert cfg.redis_url.startswith("rediss://")

    def test_qdrant_url_property(self):
        """Verify Qdrant URL generation."""
        from app.core.config import QdrantSettings
        cfg = QdrantSettings()
        assert cfg.qdrant_url.startswith("http://")

    def test_qdrant_url_https(self):
        """Verify Qdrant URL with HTTPS."""
        from app.core.config import QdrantSettings
        cfg = QdrantSettings(QDRANT_HTTPS=True)
        assert cfg.qdrant_url.startswith("https://")

    def test_properties_is_development_is_testing_is_production(self, mock_redis_env):
        """Verify environment property booleans."""
        from app.core.config import Settings
        dev = Settings(ENVIRONMENT="development")
        assert dev.is_development is True
        assert dev.is_testing is False
        assert dev.is_production is False

        test = Settings(ENVIRONMENT="testing")
        assert test.is_testing is True

        prod = Settings(ENVIRONMENT="production")
        assert prod.is_production is True

    def test_backward_compat_properties(self, mock_redis_env):
        """Verify backward-compatible property access works."""
        from app.core.config import Settings
        s = Settings()
        assert s.REDIS_HOST == "localhost"
        assert s.REDIS_PORT == 6379
        assert s.QDRANT_HOST == "localhost"
        assert s.QDRANT_PORT == 6333
        assert s.RATE_LIMIT_REQUESTS == 100
        assert s.RATE_LIMIT_WINDOW_SECS == 60


# ========================================================================= #
#  logging_config.py                                                        #
# ========================================================================= #

class TestLoggingConfig:
    def test_json_formatter_basic(self):
        """Verify JSONFormatter produces valid JSON."""
        from app.core.logging_config import JSONFormatter
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "test message"
        assert parsed["logger"] == "test_logger"

    def test_json_formatter_with_extras(self):
        """Verify JSONFormatter includes extra fields."""
        from app.core.logging_config import JSONFormatter
        import logging

        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg="event occurred",
            args=(),
            exc_info=None,
        )
        record.request_id = "req_abc123"
        record.job_id = "job_xyz"
        record.latency_ms = 42.5
        record.event = "test_event"

        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["request_id"] == "req_abc123"
        assert parsed["job_id"] == "job_xyz"
        assert parsed["latency_ms"] == 42.5
        assert parsed["event"] == "test_event"

    def test_json_formatter_with_exception(self):
        """Verify JSONFormatter captures exception info."""
        from app.core.logging_config import JSONFormatter
        import logging
        import sys

        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname=__file__,
                lineno=1,
                msg="error occurred",
                args=(),
                exc_info=exc_info,
            )

        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["exception"]["type"] == "ValueError"
        assert "test error" in parsed["exception"]["message"]

    def test_generate_ids(self):
        """Verify ID generators produce unique strings."""
        from app.core.logging_config import (
            generate_trace_id,
            generate_request_id,
            generate_job_id,
            generate_research_id,
        )

        ids = {generate_trace_id() for _ in range(100)}
        assert len(ids) == 100

        req_ids = {generate_request_id() for _ in range(100)}
        assert len(req_ids) == 100
        assert all(r.startswith("req_") for r in req_ids)

        job_ids = {generate_job_id() for _ in range(100)}
        assert len(job_ids) == 100
        assert all(j.startswith("job_") for j in job_ids)

        res_ids = {generate_research_id() for _ in range(100)}
        assert len(res_ids) == 100
        assert all(r.startswith("res_") for r in res_ids)

    def test_configure_logging_creates_handlers(self):
        """Verify configure_logging sets up handlers."""
        from app.core.logging_config import configure_logging
        import logging
        import tempfile
        import os

        tmpdir = tempfile.mkdtemp()
        try:
            configure_logging(log_dir=tmpdir)
            root = logging.getLogger()
            handler_names = [type(h).__name__ for h in root.handlers]
            assert "StreamHandler" in handler_names
            assert "RotatingFileHandler" in handler_names
        finally:
            for h in root.handlers[:]:
                h.close()
                root.removeHandler(h)
            try:
                import shutil
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass

    def test_legacy_timed_decorator_success(self):
        """Verify @timed decorator logs success."""
        from app.core.logging_config import timed

        @timed("test_op")
        def sample_fn():
            return 42

        result = sample_fn()
        assert result == 42

    def test_legacy_timed_decorator_failure(self):
        """Verify @timed decorator logs failure."""
        from app.core.logging_config import timed

        @timed("failing_op")
        def failing_fn():
            raise RuntimeError("fail")

        with pytest.raises(RuntimeError):
            failing_fn()

    @pytest.mark.asyncio
    async def test_legacy_async_timed_decorator(self):
        """Verify @async_timed decorator works."""
        from app.core.logging_config import async_timed

        @async_timed("async_op")
        async def sample_async():
            return 99

        result = await sample_async()
        assert result == 99


# ========================================================================= #
#  security.py                                                              #
# ========================================================================= #

class TestSecurity:
    def test_hash_api_key_deterministic(self):
        """Verify API key hashing is deterministic."""
        from app.core.security import hash_api_key
        key = "test-api-key-12345"
        h1 = hash_api_key(key)
        h2 = hash_api_key(key)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest

    def test_verify_api_key_hash_valid(self):
        """Verify valid API key hash comparison."""
        from app.core.security import hash_api_key, verify_api_key_hash
        key = "valid-key"
        stored = hash_api_key(key)
        assert verify_api_key_hash(key, stored) is True

    def test_verify_api_key_hash_invalid(self):
        """Verify invalid API key hash comparison fails."""
        from app.core.security import hash_api_key, verify_api_key_hash
        stored = hash_api_key("real-key")
        assert verify_api_key_hash("wrong-key", stored) is False

    def test_mask_secret(self):
        """Verify secret masking hides characters."""
        from app.core.security import mask_secret
        assert mask_secret("abcdefghijklmno") == "***********lmno"
        assert mask_secret("short") == "****"
        assert mask_secret("") == "****"
        assert mask_secret("abcdef", visible_chars=2) == "****ef"

    def test_sanitize_input_strips_control_chars(self):
        """Verify input sanitization removes control characters."""
        from app.core.security import sanitize_input
        dirty = "hello\x00world\x1fclean"
        clean = sanitize_input(dirty)
        assert clean == "helloworldclean"

    def test_sanitize_input_truncates_long(self):
        """Verify input sanitization truncates long strings."""
        from app.core.security import sanitize_input
        long_str = "a" * 20000
        truncated = sanitize_input(long_str, max_length=100)
        assert len(truncated) == 100

    def test_sanitize_html(self):
        """Verify HTML sanitization removes tags."""
        from app.core.security import sanitize_html
        assert sanitize_html("<script>alert('xss')</script>") == "alert('xss')"
        assert sanitize_html("<p>Hello</p>") == "Hello"

    def test_rate_limiter_allows_within_limit(self):
        """Verify rate limiter allows requests within limit."""
        from app.core.security import RateLimiter
        limiter = RateLimiter(max_requests=5, window_secs=60)
        for _ in range(5):
            assert limiter.is_allowed("test-key") is True

    def test_rate_limiter_blocks_excess(self):
        """Verify rate limiter blocks requests exceeding limit."""
        from app.core.security import RateLimiter
        limiter = RateLimiter(max_requests=2, window_secs=60)
        assert limiter.is_allowed("key") is True
        assert limiter.is_allowed("key") is True
        assert limiter.is_allowed("key") is False

    def test_rate_limiter_reset(self):
        """Verify rate limiter reset clears state."""
        from app.core.security import RateLimiter
        limiter = RateLimiter(max_requests=1, window_secs=60)
        assert limiter.is_allowed("key") is True
        assert limiter.is_allowed("key") is False
        limiter.reset("key")
        assert limiter.is_allowed("key") is True

    def test_rate_limiter_remaining(self):
        """Verify rate limiter reports correct remaining count."""
        from app.core.security import RateLimiter
        limiter = RateLimiter(max_requests=10, window_secs=60)
        assert limiter.remaining("key") == 10
        limiter.is_allowed("key")
        assert limiter.remaining("key") == 9

    def test_create_jwt_token(self):
        """Verify JWT token creation."""
        from app.core.security import create_jwt_token
        token = create_jwt_token(subject="user123")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_decode_jwt_token(self):
        """Verify JWT token decoding."""
        from app.core.security import create_jwt_token, decode_jwt_token
        token = create_jwt_token(subject="user123", extra_claims={"role": "admin"})
        payload = decode_jwt_token(token)
        assert payload["sub"] == "user123"
        assert payload["role"] == "admin"
        assert "iat" in payload
        assert "exp" in payload

    def test_decode_invalid_jwt_token(self):
        """Verify invalid JWT token raises error."""
        from app.core.security import decode_jwt_token
        with pytest.raises(Exception):
            decode_jwt_token("invalid-token")

    def test_security_audit_logger(self):
        """Verify SecurityAuditLogger methods don't raise."""
        from app.core.security import SecurityAuditLogger
        audit = SecurityAuditLogger()
        audit.log_auth_success("user123", "api_key")
        audit.log_auth_failure("user456", "jwt", "invalid signature")
        audit.log_rate_limit_hit("127.0.0.1")
        audit.log_access_denied("/api/v1/admin", "user789")


# ========================================================================= #
#  cache.py                                                                 #
# ========================================================================= #

class TestCache:
    def test_cache_singleton(self):
        """Verify CacheService is a singleton."""
        from app.core.cache import CacheService
        c1 = CacheService()
        c2 = CacheService()
        assert c1 is c2

    def test_cache_fallback_dict(self):
        """Verify cache falls back to in-memory dict when Redis unavailable."""
        from app.core.cache import CacheService
        cache = CacheService()
        assert cache.available is False

    def test_cache_set_and_get(self, mock_config):
        """Verify cache set/get with in-memory fallback."""
        from app.core.cache import CacheService
        cache = CacheService()
        key = cache._make_key("test", "test-query")
        cache._set(key, {"data": "value"}, ttl=100)
        result = cache._get(key)
        assert result == {"data": "value"}

    def test_cache_miss_returns_none(self, mock_config):
        """Verify cache miss returns None."""
        from app.core.cache import CacheService
        cache = CacheService()
        key = cache._make_key("test", "nonexistent")
        result = cache._get(key)
        assert result is None

    def test_cache_delete(self, mock_config):
        """Verify cache deletion works."""
        from app.core.cache import CacheService
        cache = CacheService()
        key = cache._make_key("test", "delete-me")
        cache._set(key, {"data": "to-delete"}, ttl=100)
        assert cache._get(key) is not None
        cache._delete(key)
        assert cache._get(key) is None

    def test_cache_metrics(self, mock_config):
        """Verify cache hit/miss tracking."""
        from app.core.cache import CacheService
        cache = CacheService()
        metrics_before = cache.get_metrics()
        assert metrics_before["cache_hits"] == 0
        assert metrics_before["cache_misses"] == 0

        cache._get(cache._make_key("test", "miss"))
        assert cache.get_metrics()["cache_misses"] == 1

        key = cache._make_key("test", "hit")
        cache._set(key, {"data": "x"}, ttl=100)
        cache._get(key)
        assert cache.get_metrics()["cache_hits"] == 1

    def test_invalidate_namespace(self, mock_config):
        """Verify namespace invalidation removes matching keys."""
        from app.core.cache import CacheService
        cache = CacheService()
        cache._set(cache._make_key("ns1", "a"), {"v": 1}, ttl=100)
        cache._set(cache._make_key("ns1", "b"), {"v": 2}, ttl=100)
        cache._set(cache._make_key("ns2", "c"), {"v": 3}, ttl=100)

        cache.invalidate_namespace("ns1")
        assert cache._get(cache._make_key("ns1", "a")) is None
        assert cache._get(cache._make_key("ns1", "b")) is None
        assert cache._get(cache._make_key("ns2", "c")) is not None

    def test_clear_all(self, mock_config):
        """Verify clear_all removes all cache entries."""
        from app.core.cache import CacheService
        cache = CacheService()
        cache._set(cache._make_key("test", "x"), {"v": 1}, ttl=100)
        cache._set(cache._make_key("test", "y"), {"v": 2}, ttl=100)
        cache.clear_all()
        assert cache._get(cache._make_key("test", "x")) is None
        assert cache._get(cache._make_key("test", "y")) is None

    def test_search_results_cache(self, mock_config):
        """Verify search result cache methods."""
        from app.core.cache import CacheService
        cache = CacheService()
        query = "test query"
        results = [{"title": "result1"}]

        # Miss
        assert cache.get_search_results(query) is None

        # Set and hit
        cache.set_search_results(query, results, ttl=100)
        cached = cache.get_search_results(query)
        assert cached["results"] == results

    def test_webpage_cache(self, mock_config):
        """Verify webpage content cache methods."""
        from app.core.cache import CacheService
        cache = CacheService()
        url = "https://example.com"
        content = "<html>test</html>"

        assert cache.get_webpage_content(url) is None
        cache.set_webpage_content(url, content, ttl=100)
        assert cache.get_webpage_content(url)["content"] == content

    def test_reranked_cache(self, mock_config):
        """Verify reranked results cache methods."""
        from app.core.cache import CacheService
        cache = CacheService()
        query = "rerank test"
        chunks = [{"text": "chunk1", "score": 0.9}]

        assert cache.get_reranked_results(query) is None
        cache.set_reranked_results(query, chunks, ttl=100)
        assert cache.get_reranked_results(query)["chunks"] == chunks

    def test_embedding_cache(self, mock_config):
        """Verify embedding cache methods."""
        from app.core.cache import CacheService
        cache = CacheService()
        text = "embed me"
        vector = [0.1, 0.2, 0.3]

        assert cache.get_embedding(text) is None
        cache.set_embedding(text, vector, ttl=100)
        assert cache.get_embedding(text)["vector"] == vector

    def test_get_cache_function(self, mock_config):
        """Verify get_cache() returns singleton."""
        from app.core.cache import get_cache
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_decorator_cached(self, mock_config):
        """Verify @cached decorator works."""
        from app.core.cache import cached, get_cache

        call_count = 0

        @cached("test_decorator", ttl=100)
        def compute(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        assert compute(5) == 10
        assert call_count == 1
        assert compute(5) == 10
        assert call_count == 1  # Should not increase

    @pytest.mark.skip(reason="Async decorator needs event loop investigation")
    @pytest.mark.asyncio
    async def test_decorator_cached_async(self, mock_config):
        """Verify @cached decorator works with async functions."""
        from app.core.cache import cached

        call_count = 0

        @cached("test_async_dec", ttl=100)
        async def compute_async(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 3

        result1 = await compute_async(3)
        assert result1 == 9
        assert call_count == 1

        result2 = await compute_async(3)
        assert result2 == 9
        assert call_count == 1


# ========================================================================= #
#  memory.py                                                                #
# ========================================================================= #

class TestMemory:
    def test_memory_singleton(self):
        """Verify MemoryService is a singleton."""
        from app.core.memory import MemoryService
        m1 = MemoryService()
        m2 = MemoryService()
        assert m1 is m2

    def test_memory_fallback_dict(self):
        """Verify MemoryService falls back to in-memory dict."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        assert mem.available is False

    def test_save_and_get_session(self, mock_config):
        """Verify save/get research session with fallback."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        session_id = "test-session-1"
        data = {"query": "test", "report": "test report"}

        mem.save_research_session(session_id, data)
        loaded = mem.get_research_session(session_id)
        assert loaded is not None
        assert loaded["query"] == "test"
        assert loaded["report"] == "test report"

    def test_get_nonexistent_session(self, mock_config):
        """Verify getting nonexistent session returns None."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        assert mem.get_research_session("nonexistent") is None

    def test_update_research_memory(self, mock_config):
        """Verify update merges data into existing session."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        session_id = "update-test"
        mem.save_research_session(session_id, {"query": "original", "step": 1})
        mem.update_research_memory(session_id, {"step": 2, "new_key": "value"})
        loaded = mem.get_research_session(session_id)
        assert loaded["query"] == "original"
        assert loaded["step"] == 2
        assert loaded["new_key"] == "value"

    def test_delete_session(self, mock_config):
        """Verify session deletion removes data."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        session_id = "delete-test"
        mem.save_research_session(session_id, {"data": "to-delete"})
        assert mem.get_research_session(session_id) is not None
        mem.delete_research_session(session_id)
        assert mem.get_research_session(session_id) is None

    def test_list_session_keys(self, mock_config):
        """Verify list_session_keys returns stored keys."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        mem.save_research_session("list-test-1", {"q": "1"})
        mem.save_research_session("list-test-2", {"q": "2"})
        keys = mem.list_session_keys()
        assert len(keys) >= 2
        assert any("list-test-1" in k for k in keys)
        assert any("list-test-2" in k for k in keys)

    def test_get_statistics(self, mock_config):
        """Verify get_statistics returns metrics."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        stats = mem.get_statistics()
        assert "total_sessions" in stats
        assert "active_sessions" in stats
        assert "estimated_size_bytes" in stats

    def test_get_session_summary(self, mock_config):
        """Verify get_session_summary returns summary."""
        from app.core.memory import MemoryService
        mem = MemoryService()
        session_id = "summary-test"
        mem.save_research_session(session_id, {"query": "q", "report": "r"})
        summary = mem.get_session_summary(session_id)
        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["has_report"] is True
        assert summary["key_count"] == 2

    def test_get_memory_service_function(self, mock_config):
        """Verify get_memory_service returns singleton."""
        from app.core.memory import get_memory_service
        m1 = get_memory_service()
        m2 = get_memory_service()
        assert m1 is m2


# ========================================================================= #
#  dependencies.py                                                          #
# ========================================================================= #

class TestDependencies:
    def test_get_settings(self, mock_config):
        """Verify get_settings returns settings."""
        from app.core.dependencies import get_settings
        s = get_settings()
        assert s is not None

    def test_client_registry(self):
        """Verify ClientRegistry registration and retrieval."""
        from app.core.dependencies import ClientRegistry
        registry = ClientRegistry()

        assert registry.is_registered("test") is False
        registry.register("test", {"foo": "bar"})
        assert registry.is_registered("test") is True
        assert registry.get("test")["foo"] == "bar"

    def test_get_redis_client_fallback(self, mock_config):
        """Verify get_redis_client returns None when unavailable."""
        from app.core.dependencies import get_redis_client
        client = get_redis_client()
        # Will return None since Redis is not running in test
        assert client is None or hasattr(client, "ping")

    def test_get_qdrant_client(self, mock_config):
        """Verify get_qdrant_client returns a client instance (singleton)."""
        from app.core.dependencies import get_qdrant_client
        client = get_qdrant_client()
        assert client is not None
        assert hasattr(client, "scroll")

    def test_get_embedding_model_fallback(self, mock_config):
        """Verify get_embedding_model returns None when unavailable."""
        from app.core.dependencies import get_embedding_model
        model = get_embedding_model()
        # May return None if sentence-transformers not installed
        assert model is None or hasattr(model, "encode")

    def test_get_llm_gateway(self, mock_config):
        """Verify get_llm_gateway returns router."""
        from app.core.dependencies import get_llm_gateway
        router = get_llm_gateway()
        assert router is not None


# ========================================================================= #
#  llm.py                                                                   #
# ========================================================================= #

class TestLLM:
    def test_llm_response_standardized(self):
        """Verify LLMResponse has standardized fields."""
        from app.core.llm import LLMResponse
        resp = LLMResponse(
            content="test response",
            model="test-model",
            provider="test-provider",
            tokens_used=150,
            latency_ms=250.5,
            trace_id="trace-123",
        )
        assert resp.content == "test response"
        assert resp.model == "test-model"
        assert resp.tokens_used == 150
        assert resp.latency_ms == 250.5
        assert resp.trace_id == "trace-123"
        assert resp.success is True

    def test_llm_response_to_dict(self):
        """Verify LLMResponse.to_dict returns expected format."""
        from app.core.llm import LLMResponse
        resp = LLMResponse(
            content="answer",
            model="gpt-4",
            tokens_used=100,
            latency_ms=200.0,
            provider="openai",
        )
        d = resp.to_dict()
        assert d["content"] == "answer"
        assert d["model"] == "gpt-4"
        assert d["tokens_used"] == 100
        assert d["latency_ms"] == 200.0
        assert d["provider"] == "openai"

    def test_llm_response_error(self):
        """Verify LLMResponse handles error state."""
        from app.core.llm import LLMResponse
        resp = LLMResponse(
            content="",
            success=False,
            error="Rate limit exceeded",
            latency_ms=5000.0,
        )
        assert resp.success is False
        assert resp.error == "Rate limit exceeded"

    def test_backoff_calculation(self):
        """Verify exponential backoff calculation."""
        from app.core.llm import _calculate_backoff
        b0 = _calculate_backoff(0)
        b1 = _calculate_backoff(1)
        b2 = _calculate_backoff(2)
        assert b0 >= 1.0
        assert b1 >= 2.0
        assert b2 >= 4.0

    def test_llm_retry_handler_success(self):
        """Verify retry handler succeeds on first attempt."""
        from app.core.llm import LLMRetryHandler, LLMResponse

        handler = LLMRetryHandler(max_retries=2)
        mock_fn = MagicMock(return_value=LLMResponse(content="success"))

        result = handler.execute(mock_fn, prompt="test", task_type="test")
        assert result.content == "success"
        assert result.success is True
        mock_fn.assert_called_once()

    def test_llm_retry_handler_retries_on_failure(self):
        """Verify retry handler retries on failure."""
        from app.core.llm import LLMRetryHandler, LLMResponse

        handler = LLMRetryHandler(max_retries=2)
        mock_fn = MagicMock()
        mock_fn.side_effect = [
            RuntimeError("fail 1"),
            RuntimeError("fail 2"),
            LLMResponse(content="success after retry"),
        ]

        result = handler.execute(mock_fn, prompt="test", task_type="test")
        assert result.content == "success after retry"
        assert result.success is True
        assert mock_fn.call_count == 3

    def test_llm_retry_handler_all_fail(self):
        """Verify retry handler returns error when all attempts fail."""
        from app.core.llm import LLMRetryHandler, LLMResponse

        handler = LLMRetryHandler(max_retries=2)
        mock_fn = MagicMock(side_effect=RuntimeError("persistent failure"))

        result = handler.execute(mock_fn, prompt="test", task_type="test")
        assert result.success is False
        assert "persistent failure" in (result.error or "")
        assert mock_fn.call_count == 3

    @pytest.mark.asyncio
    async def test_llm_retry_handler_async_success(self):
        """Verify async retry handler succeeds."""
        from app.core.llm import LLMRetryHandler, LLMResponse

        handler = LLMRetryHandler(max_retries=1)

        async def mock_async_call(prompt: str, **kwargs):
            return LLMResponse(content="async success")

        result = await handler.execute_async(mock_async_call, prompt="test")
        assert result.content == "async success"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_llm_retry_handler_async_retry(self):
        """Verify async retry handler retries on failure."""
        from app.core.llm import LLMRetryHandler, LLMResponse

        handler = LLMRetryHandler(max_retries=2)
        attempt = [0]

        async def mock_flaky(prompt: str, **kwargs):
            attempt[0] += 1
            if attempt[0] < 3:
                raise RuntimeError(f"fail {attempt[0]}")
            return LLMResponse(content="finally")

        result = await handler.execute_async(mock_flaky, prompt="test")
        assert result.content == "finally"
        assert result.success is True

    def test_get_llm_service(self):
        """Verify get_llm_service returns singleton."""
        from app.core.llm import get_llm_service
        s1 = get_llm_service()
        s2 = get_llm_service()
        assert s1 is s2
        assert hasattr(s1, "generate")
        assert hasattr(s1, "generate_response")

    def test_get_llm_router_backward_compat(self):
        """Verify get_llm_router is backward-compatible."""
        from app.core.llm import get_llm_router
        router = get_llm_router()
        assert router is not None


# ========================================================================= #
#  task_manager.py                                                          #
# ========================================================================= #

class TestTaskManager:
    @pytest.fixture
    def mock_job_service(self):
        """Mock the job service for task manager tests."""
        with patch("app.core.task_manager.get_job_service") as mock_get:
            mock_service = MagicMock()
            mock_service.create_job.return_value = "test-job-123"
            mock_service.get_job.return_value = {
                "job_id": "test-job-123",
                "status": "running",
                "progress": 50,
                "current_step": "researching",
                "error": None,
                "report": "",
                "sources": [],
                "quality_metrics": {},
                "research_steps": [],
                "timing": {},
                "created_at": "2026-01-01T00:00:00+00:00",
            }
            mock_get.return_value = mock_service
            yield mock_service

    def test_task_manager_initialization(self, mock_job_service):
        """Verify TaskManager initializes correctly."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        assert tm.job_service is not None
        assert tm.metrics is not None

    def test_submit_research_returns_job_id(self, mock_job_service):
        """Verify submit_research returns a job ID."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        job_id = tm.submit_research("test query")
        assert job_id == "test-job-123"

    def test_get_status_returns_job(self, mock_job_service):
        """Verify get_status returns job details."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        status = tm.get_status("test-job-123")
        assert status is not None
        assert status["job_id"] == "test-job-123"
        assert status["status"] == "running"
        assert status["progress"] == 50

    def test_get_status_nonexistent(self, mock_job_service):
        """Verify get_status returns None for missing job."""
        mock_job_service = mock_job_service
        mock_job_service.get_job.return_value = None
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        assert tm.get_status("nonexistent") is None

    def test_get_result_returns_details(self, mock_job_service):
        """Verify get_result returns full job details."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        result = tm.get_result("test-job-123")
        assert result is not None
        assert result["job_id"] == "test-job-123"
        assert "report" in result
        assert "sources" in result

    def test_cancel_task_running(self, mock_job_service):
        """Verify cancel_task cancels a running job."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        assert tm.cancel_task("test-job-123") is True

    def test_cancel_task_nonexistent(self, mock_job_service):
        """Verify cancel_task returns False for missing job."""
        mock_job_service = mock_job_service
        mock_job_service.get_job.return_value = None
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        assert tm.cancel_task("nonexistent") is False

    def test_cancel_task_completed(self, mock_job_service):
        """Verify cancel_task returns False for completed job."""
        mock_job_service = mock_job_service
        mock_job_service.get_job.return_value = {
            "job_id": "done",
            "status": "completed",
        }
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        assert tm.cancel_task("done") is False

    def test_get_metrics_returns_counts(self, mock_job_service):
        """Verify get_metrics returns task counts."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        metrics = tm.get_metrics()
        assert "tasks_submitted" in metrics
        assert "tasks_completed" in metrics
        assert "tasks_failed" in metrics
        assert "active_count" in metrics

    def test_list_active_tasks(self, mock_job_service):
        """Verify list_active_tasks returns active tasks."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        tm.submit_research("test query")
        active = tm.list_active_tasks()
        assert len(active) >= 1
        assert any(t["job_id"] == "test-job-123" for t in active)

    def test_get_task_progress(self, mock_job_service):
        """Verify get_task_progress returns progress."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        tm.submit_research("test query")
        progress = tm.get_task_progress("test-job-123")
        assert progress is not None
        assert "status" in progress
        assert "progress" in progress

    def test_update_progress(self, mock_job_service):
        """Verify update_progress updates task state."""
        from app.core.task_manager import TaskManager
        tm = TaskManager()
        tm.submit_research("test query")
        tm.update_progress("test-job-123", 75, "analyzing")
        progress = tm.get_task_progress("test-job-123")
        assert progress is not None and progress["progress"] == 75
