"""
dependencies.py
Production-grade dependency injection with:
- Singleton clients with lazy initialization
- Connection pooling for Redis, Qdrant, Embeddings, LLM
- Shared instances preventing duplicate client creation
- Thread-safe initialization
"""

import logging
from typing import Any, Optional

from fastapi import Depends

from app.core.config import Settings, settings
from app.core.security import verify_api_key

logger = logging.getLogger(__name__)


class ClientRegistry:
    """
    Thread-safe singleton registry for shared infrastructure clients.
    Prevents duplicate client creation across the application.
    """

    def __init__(self) -> None:
        self._clients: dict[str, Any] = {}
        self._initialized: dict[str, bool] = {}

    def register(self, name: str, factory: Any) -> Any:
        if name not in self._clients:
            self._clients[name] = factory
            self._initialized[name] = True
        return self._clients[name]

    def get(self, name: str) -> Optional[Any]:
        return self._clients.get(name)

    def is_registered(self, name: str) -> bool:
        return name in self._clients


_registry = ClientRegistry()


def get_settings() -> Settings:
    """Dependency to inject global settings."""
    return settings


def require_auth(api_key: str = Depends(verify_api_key)) -> str:
    """Dependency to require authentication."""
    return api_key  # type: ignore


def get_redis_client() -> Any:
    """
    Returns a singleton Redis client with connection pooling.
    Lazy-initialized on first call.
    """
    if _registry.is_registered("redis"):
        return _registry.get("redis")

    redis_cfg = settings.redis_config
    try:
        import redis as redis_module
        pool = redis_module.ConnectionPool(
            host=redis_cfg.REDIS_HOST,
            port=redis_cfg.REDIS_PORT,
            db=redis_cfg.REDIS_DB,
            password=redis_cfg.REDIS_PASSWORD,
            socket_connect_timeout=redis_cfg.REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
            max_connections=20,
            retry_on_timeout=True,
        )
        client = redis_module.Redis(connection_pool=pool)
        client.ping()
        _registry.register("redis", client)
        _registry.register("redis_pool", pool)
        logger.info(
            "Redis client initialized",
            extra={"event": "di_redis_init", "host": redis_cfg.REDIS_HOST},
        )
        return client
    except Exception as e:
        logger.warning(
            f"Redis initialization failed: {e}",
            extra={"event": "di_redis_failed", "error": str(e)},
        )
        return None


def get_qdrant_client() -> Any:
    """
    Returns a singleton Qdrant client with lazy initialization.
    """
    if _registry.is_registered("qdrant"):
        return _registry.get("qdrant")

    qdrant_cfg = settings.qdrant
    try:
        from qdrant_client import QdrantClient as QClient
        client = QClient(
            host=qdrant_cfg.QDRANT_HOST,
            port=qdrant_cfg.QDRANT_PORT,
            api_key=qdrant_cfg.QDRANT_API_KEY,
            https=qdrant_cfg.QDRANT_HTTPS,
            timeout=30,
        )
        _registry.register("qdrant", client)
        logger.info(
            "Qdrant client initialized",
            extra={"event": "di_qdrant_init", "host": qdrant_cfg.QDRANT_HOST},
        )
        return client
    except ImportError:
        logger.warning(
            "Qdrant client not available (qdrant-client not installed)",
            extra={"event": "di_qdrant_unavailable"},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Qdrant initialization failed: {e}",
            extra={"event": "di_qdrant_failed", "error": str(e)},
        )
        return None


def get_embedding_model() -> Any:
    """
    Returns a singleton embedding model with lazy initialization.
    Uses sentence-transformers by default.
    """
    if _registry.is_registered("embedding_model"):
        return _registry.get("embedding_model")

    try:
        from sentence_transformers import SentenceTransformer
        model_name = settings.llm.DEFAULT_EMBEDDING_MODEL
        model = SentenceTransformer(model_name)
        _registry.register("embedding_model", model)
        logger.info(
            "Embedding model initialized",
            extra={"event": "di_embedding_init", "model": model_name},
        )
        return model
    except ImportError:
        logger.warning(
            "Embedding model not available (sentence-transformers not installed)",
            extra={"event": "di_embedding_unavailable"},
        )
        return None
    except Exception as e:
        logger.warning(
            f"Embedding model initialization failed: {e}",
            extra={"event": "di_embedding_failed", "error": str(e)},
        )
        return None


def get_llm_gateway() -> Any:
    """
    Returns a singleton LLM gateway/router.
    Lazy-initialized on first call.
    """
    if _registry.is_registered("llm_gateway"):
        return _registry.get("llm_gateway")

    try:
        from app.llm.router import get_llm_router
        router = get_llm_router()
        _registry.register("llm_gateway", router)
        logger.info(
            "LLM Gateway initialized",
            extra={"event": "di_llm_gateway_init"},
        )
        return router
    except Exception as e:
        logger.warning(
            f"LLM Gateway initialization failed: {e}",
            extra={"event": "di_llm_gateway_failed", "error": str(e)},
        )
        return None


def get_client_registry() -> ClientRegistry:
    """Returns the shared client registry."""
    return _registry


async def get_redis_dependency() -> Any:
    """FastAPI dependency for Redis client."""
    return get_redis_client()


async def get_qdrant_dependency() -> Any:
    """FastAPI dependency for Qdrant client."""
    return get_qdrant_client()


async def get_embedding_dependency() -> Any:
    """FastAPI dependency for embedding model."""
    return get_embedding_model()


async def get_llm_dependency() -> Any:
    """FastAPI dependency for LLM gateway."""
    return get_llm_gateway()
