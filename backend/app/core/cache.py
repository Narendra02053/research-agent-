"""
cache.py
Redis-backed caching layer for the AI Deep Research Agent.
Caches Tavily search results, extracted webpage content, and reranked outputs
to reduce repeated API calls and improve overall pipeline performance.
"""

import os
import json
import hashlib
import logging
import redis

logger = logging.getLogger(__name__)

class CacheService:
    """
    Reusable Redis cache client. Handles connection, serialization,
    and graceful fallback if Redis is unavailable.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            try:
                cls._instance.client = redis.Redis(
                    host=host, port=port, db=0, decode_responses=True,
                    socket_connect_timeout=2
                )
                cls._instance.client.ping()
                cls._instance.available = True
                logger.info(f"Redis cache connected at {host}:{port}")
            except Exception as e:
                cls._instance.available = False
                cls._instance.client = None
                logger.warning(f"Redis unavailable ({e}). Cache layer disabled — system will run without caching.")
        return cls._instance

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_key(namespace: str, raw: str) -> str:
        digest = hashlib.md5(raw.encode()).hexdigest()
        return f"deep_research:{namespace}:{digest}"

    def _set(self, key: str, value: dict, ttl: int):
        if not self.available:
            return
        try:
            self.client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Cache SET failed for key '{key}': {e}")

    def _get(self, key: str):
        if not self.available:
            return None
        try:
            raw = self.client.get(key)
            return json.loads(raw) if raw else None
        except Exception as e:
            logger.warning(f"Cache GET failed for key '{key}': {e}")
            return None

    def _delete(self, key: str):
        if not self.available:
            return
        try:
            self.client.delete(key)
        except Exception as e:
            logger.warning(f"Cache DELETE failed for key '{key}': {e}")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #
    def get_search_results(self, query: str):
        key = self._make_key("search", query)
        result = self._get(key)
        if result:
            logger.info(f"Cache HIT  [search] query='{query[:60]}'")
        return result

    def set_search_results(self, query: str, results: list, ttl: int = 3600):
        key = self._make_key("search", query)
        self._set(key, {"results": results}, ttl)
        logger.info(f"Cache SET  [search] query='{query[:60]}'  ttl={ttl}s")

    def get_webpage_content(self, url: str):
        key = self._make_key("webpage", url)
        result = self._get(key)
        if result:
            logger.info(f"Cache HIT  [webpage] url='{url[:80]}'")
        return result

    def set_webpage_content(self, url: str, content: str, ttl: int = 7200):
        key = self._make_key("webpage", url)
        self._set(key, {"content": content}, ttl)
        logger.info(f"Cache SET  [webpage] url='{url[:80]}'  ttl={ttl}s")

    def get_reranked_results(self, query: str):
        key = self._make_key("reranked", query)
        result = self._get(key)
        if result:
            logger.info(f"Cache HIT  [reranked] query='{query[:60]}'")
        return result

    def set_reranked_results(self, query: str, chunks: list, ttl: int = 1800):
        key = self._make_key("reranked", query)
        self._set(key, {"chunks": chunks}, ttl)
        logger.info(f"Cache SET  [reranked] query='{query[:60]}'  ttl={ttl}s")

    def get_embedding(self, text: str):
        key = self._make_key("embedding", text)
        result = self._get(key)
        if result:
            logger.info("Cache HIT  [embedding]")
        return result

    def set_embedding(self, text: str, vector: list, ttl: int = 86400):
        key = self._make_key("embedding", text)
        self._set(key, {"vector": vector}, ttl)

    def invalidate_session(self, session_id: str):
        """Remove all keys associated with a session."""
        if not self.available:
            return
        pattern = f"deep_research:session:{session_id}:*"
        for key in self.client.scan_iter(pattern):
            self._delete(key)
        logger.info(f"Invalidated all cache keys for session '{session_id}'")


def get_cache() -> CacheService:
    return CacheService()
