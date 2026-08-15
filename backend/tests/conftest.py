# conftest.py - Fixtures and configuration for backend tests.
"""
Shared test fixtures for core module tests.
"""
import os
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    from app.core.cache import CacheService
    from app.core.memory import MemoryService

    CacheService._instance = None
    CacheService._fallback = {}
    MemoryService._instance = None
    MemoryService._fallback = {}

    yield


@pytest.fixture(autouse=True)
def fast_redis_fallback():
    """Mock Redis to fail instantly, using in-memory fallback in tests."""
    with patch("redis.ConnectionPool", side_effect=Exception("Redis not available in tests")):
        yield


@pytest.fixture
def mock_redis_env():
    """Set up minimal Redis env vars for testing."""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["REDIS_HOST"] = "localhost"
    os.environ["REDIS_PORT"] = "6379"
    os.environ["REDIS_PASSWORD"] = ""
    os.environ["TAVILY_API_KEY"] = "test-tavily-key"
    os.environ["GROQ_API_KEY"] = "test-groq-key"
    yield
    for k in ["ENVIRONMENT", "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
              "TAVILY_API_KEY", "GROQ_API_KEY"]:
        os.environ.pop(k, None)


@pytest.fixture
def mock_config():
    """Provide a mock settings object for testing."""
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.ENVIRONMENT = "testing"
        mock_settings.is_development = False
        mock_settings.is_testing = True
        mock_settings.is_production = False
        mock_settings.LOG_LEVEL = "DEBUG"
        mock_settings.PROJECT_NAME = "Test"
        mock_settings.VERSION = "0.0.0"

        mock_settings.llm.DEFAULT_LLM_MODEL = "test-model"
        mock_settings.llm.DEFAULT_EMBEDDING_MODEL = "test-embedding"
        mock_settings.llm.GROQ_API_KEY = "test-groq"
        mock_settings.llm.OPENAI_API_KEY = ""
        mock_settings.llm.OLLAMA_BASE_URL = "http://localhost:11434"

        mock_settings.redis_config.REDIS_HOST = "localhost"
        mock_settings.redis_config.REDIS_PORT = 6379
        mock_settings.redis_config.REDIS_DB = 0
        mock_settings.redis_config.REDIS_PASSWORD = None
        mock_settings.redis_config.REDIS_SOCKET_TIMEOUT = 2

        mock_settings.qdrant.QDRANT_HOST = "localhost"
        mock_settings.qdrant.QDRANT_PORT = 6333
        mock_settings.qdrant.QDRANT_API_KEY = None
        mock_settings.qdrant.QDRANT_HTTPS = False

        mock_settings.security.JWT_SECRET_KEY = "test-secret"
        mock_settings.security.JWT_ALGORITHM = "HS256"
        mock_settings.security.JWT_EXPIRATION_HOURS = 24
        mock_settings.security.RATE_LIMIT_REQUESTS = 100
        mock_settings.security.RATE_LIMIT_WINDOW_SECS = 60

        mock_settings.tavily.TAVILY_API_KEY = "test-tavily"

        mock_settings.MAX_SEARCH_SUBQUERIES = 2
        mock_settings.MAX_EXTRACTION_URLS = 3
        mock_settings.MAX_KG_CHUNKS = 2
        mock_settings.RETRIEVAL_CHUNK_LIMIT = 5
        mock_settings.RERANK_TOP_K = 4
        mock_settings.MAX_CONTEXT_CHARS = 12000
        mock_settings.ENABLE_KNOWLEDGE_GRAPH = False
        mock_settings.SKIP_EVALUATION = True

        mock_settings.REDIS_HOST = "localhost"
        mock_settings.REDIS_PORT = 6379
        mock_settings.QDRANT_HOST = "localhost"
        mock_settings.QDRANT_PORT = 6333
        mock_settings.RATE_LIMIT_REQUESTS = 100
        mock_settings.RATE_LIMIT_WINDOW_SECS = 60

        yield mock_settings
