# cache.py - Caching mechanisms and Redis configuration.
"""
cache.py
Production-grade Redis-backed caching layer with:
- Configurable TTL per namespace
- Cache hit/miss tracking with Prometheus-ready counters
- Decorator-based caching
- Connection pooling via config
- Graceful fallback when Redis is unavailable
"""

import os
import json
import hashlib
import inspect
import logging
import functools
import time
from typing import Any, Callable, Optional, TypeVar

from app.core.config import settings

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class CacheMetrics:
    """
    Tracks cache hit/miss rates for observability.
    Exposes counters for Prometheus integration.
    """

    def __init__(self) -> None:
        self.hits: int = 0
        self.misses: int = 0
        self._latencies: list[float] = []

    def record_hit(self, latency_ms: float) -> None:
        self.hits += 1
        self._latencies.append(latency_ms)

    def record_miss(self) -> None:
        self.misses += 1

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def snapshot(self) -> dict[str, Any]:
        return {
            "cache_hits": self.hits,
            "cache_misses": self.misses,
            "hit_rate": round(self.hit_rate, 4),
            "total_requests": self.hits + self.misses,
        }

    def reset(self) -> None:
        self.hits = 0
        self.misses = 0
        self._latencies.clear()


class CacheService:
    """
    Thread-safe Redis cache client with connection pooling,
    namespace-scoped TTLs, hit/miss tracking, and graceful
    fallback to in-memory store when Redis is unavailable.
    """

    _instance: Optional["CacheService"] = None
    _fallback: dict[str, str] = {}

    def __new__(cls) -> "CacheService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.metrics = CacheMetrics()
        self.available = False
        self.client: Any = None
        self._pool: Any = None

        redis_cfg = settings.redis_config
        try:
            import redis as redis_module
            self._pool = redis_module.ConnectionPool(
                host=redis_cfg.REDIS_HOST,
                port=redis_cfg.REDIS_PORT,
                db=redis_cfg.REDIS_DB,
                password=redis_cfg.REDIS_PASSWORD,
                socket_connect_timeout=redis_cfg.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
            )
            self.client = redis_module.Redis(connection_pool=self._pool)
            self.client.ping()
            self.available = True
            logger.info(
                "Redis cache connected",
                extra={
                    "event": "cache_connected",
                    "host": redis_cfg.REDIS_HOST,
                    "port": redis_cfg.REDIS_PORT,
                    "db": redis_cfg.REDIS_DB,
                },
            )
        except Exception as e:
            self.available = False
            self.client = None
            logger.warning(
                f"Redis unavailable for cache ({e}). Using in-memory fallback.",
                extra={"event": "cache_disabled", "error": str(e)},
            )

    def _make_key(self, namespace: str, raw: str) -> str:
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"deep_research:{namespace}:{digest}"

    def _set(self, key: str, value: dict[str, Any], ttl: int) -> None:
        if not self.available:
            self._fallback[key] = json.dumps(value)
            return
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(
                f"Cache SET failed for key '{key}': {e}",
                extra={"event": "cache_set_error", "key": key},
            )

    def _get(self, key: str) -> Optional[dict[str, Any]]:
        t0 = time.perf_counter()
        if not self.available:
            raw = self._fallback.get(key)
            if raw:
                self.metrics.record_hit((time.perf_counter() - t0) * 1000)
                return json.loads(raw)
            self.metrics.record_miss()
            return None
        try:
            raw = self.client.get(key)
            if raw:
                self.metrics.record_hit((time.perf_counter() - t0) * 1000)
                return json.loads(raw)
            self.metrics.record_miss()
            return None
        except Exception as e:
            self.metrics.record_miss()
            logger.warning(
                f"Cache GET failed for key '{key}': {e}",
                extra={"event": "cache_get_error", "key": key},
            )
            return None

    def _delete(self, key: str) -> None:
        if not self.available:
            self._fallback.pop(key, None)
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(
                f"Cache DELETE failed for key '{key}': {e}",
                extra={"event": "cache_delete_error", "key": key},
            )

    def get_search_results(self, query: str) -> Optional[dict[str, Any]]:
        key = self._make_key("search", query)
        result = self._get(key)
        if result:
            logger.info("Cache HIT", extra={"event": "cache_hit", "namespace": "search", "key": query[:60]})
        return result

    def set_search_results(self, query: str, results: list[Any], ttl: int = 3600) -> None:
        key = self._make_key("search", query)
        self._set(key, {"results": results}, ttl)

    def get_webpage_content(self, url: str) -> Optional[dict[str, Any]]:
        key = self._make_key("webpage", url)
        result = self._get(key)
        if result:
            logger.info("Cache HIT", extra={"event": "cache_hit", "namespace": "webpage", "key": url[:80]})
        return result

    def set_webpage_content(self, url: str, content: str, ttl: int = 7200) -> None:
        key = self._make_key("webpage", url)
        self._set(key, {"content": content}, ttl)

    def get_reranked_results(self, query: str) -> Optional[dict[str, Any]]:
        key = self._make_key("reranked", query)
        result = self._get(key)
        if result:
            logger.info("Cache HIT", extra={"event": "cache_hit", "namespace": "reranked", "key": query[:60]})
        return result

    def set_reranked_results(self, query: str, chunks: list[Any], ttl: int = 1800) -> None:
        key = self._make_key("reranked", query)
        self._set(key, {"chunks": chunks}, ttl)

    def get_embedding(self, text: str) -> Optional[dict[str, Any]]:
        key = self._make_key("embedding", text)
        result = self._get(key)
        if result:
            logger.info("Cache HIT", extra={"event": "cache_hit", "namespace": "embedding"})
        return result

    def set_embedding(self, text: str, vector: list[float], ttl: int = 86400) -> None:
        key = self._make_key("embedding", text)
        self._set(key, {"vector": vector}, ttl)

    def invalidate_session(self, session_id: str) -> None:
        if not self.available:
            keys_to_delete = [k for k in self._fallback if f"deep_research:session:{session_id}:" in k]
            for k in keys_to_delete:
                self._fallback.pop(k, None)
            return
        pattern = f"deep_research:session:{session_id}:*"
        try:
            for key in self.client.scan_iter(pattern):
                self._delete(key)
        except Exception as e:
            logger.warning(
                f"Session invalidation failed: {e}",
                extra={"event": "cache_invalidation_error", "session_id": session_id},
            )

    def invalidate_namespace(self, namespace: str) -> None:
        if not self.available:
            keys_to_delete = [k for k in self._fallback if f"deep_research:{namespace}:" in k]
            for k in keys_to_delete:
                self._fallback.pop(k, None)
            return
        pattern = f"deep_research:{namespace}:*"
        try:
            for key in self.client.scan_iter(pattern):
                self._delete(key)
        except Exception as e:
            logger.warning(
                f"Namespace invalidation failed: {e}",
                extra={"event": "cache_invalidation_error", "namespace": namespace},
            )

    def clear_all(self) -> None:
        if not self.available:
            self._fallback.clear()
            return
        try:
            for key in self.client.scan_iter("deep_research:*"):
                self._delete(key)
        except Exception as e:
            logger.warning(
                f"Cache clear failed: {e}",
                extra={"event": "cache_clear_error"},
            )

    def get_metrics(self) -> dict[str, Any]:
        return self.metrics.snapshot()

    def close(self) -> None:
        if self._pool:
            self._pool.disconnect()
        self._initialized = False
        CacheService._instance = None


def cached(
    namespace: str,
    ttl: int = 3600,
    key_builder: Optional[Callable[..., str]] = None,
) -> Callable[[F], F]:
    """
    Decorator that caches function return values.

    Args:
        namespace: Cache namespace prefix
        ttl: Time-to-live in seconds
        key_builder: Optional function to build cache key from args/kwargs.
                     Defaults to str(args) + str(kwargs).

    Usage:
        @cached("search_results", ttl=1800)
        def expensive_search(query: str) -> list: ...
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                raw_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            full_key = f"deep_research:{namespace}:{cache_key}"
            cached_result = cache._get(full_key)

            if cached_result is not None:
                logger.info(
                    "Decorator cache HIT",
                    extra={"event": "decorator_cache_hit", "namespace": namespace, "function": func.__name__},
                )
                return cached_result.get("data")

            result = func(*args, **kwargs)

            cache._set(full_key, {"data": result}, ttl)
            logger.info(
                "Decorator cache SET",
                extra={"event": "decorator_cache_set", "namespace": namespace, "function": func.__name__},
            )
            return result

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            cache = get_cache()
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                raw_key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
                cache_key = hashlib.md5(raw_key.encode()).hexdigest()

            full_key = f"deep_research:{namespace}:{cache_key}"
            cached_result = cache._get(full_key)

            if cached_result is not None:
                logger.info(
                    "Decorator cache HIT",
                    extra={"event": "decorator_cache_hit", "namespace": namespace, "function": func.__name__},
                )
                return cached_result.get("data")

            result = await func(*args, **kwargs)

            cache._set(full_key, {"data": result}, ttl)
            logger.info(
                "Decorator cache SET",
                extra={"event": "decorator_cache_set", "namespace": namespace, "function": func.__name__},
            )
            return result

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return wrapper  # type: ignore
    return decorator


def get_cache() -> CacheService:
    return CacheService()
