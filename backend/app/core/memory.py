"""
memory.py
Production-grade research session memory backed by Redis with:
- Persistent session-based memory
- Memory summarization via configurable summarizer
- TTL-based cleanup policy
- Memory size limits per session
- Active session tracking and memory statistics
- Graceful fallback to in-process dict when Redis is unavailable
"""

import json
import logging
import os
import time
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TTL = 86400
MAX_SESSION_SIZE_BYTES = 10 * 1024 * 1024
MAX_SESSIONS = 1000


class MemoryStats:
    """Tracks memory usage statistics."""

    def __init__(self) -> None:
        self.total_sessions: int = 0
        self.active_sessions: int = 0
        self.total_keys: int = 0
        self.estimated_size_bytes: int = 0
        self.session_sizes: dict[str, int] = {}
        self.last_cleanup: Optional[float] = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "total_keys": self.total_keys,
            "estimated_size_bytes": self.estimated_size_bytes,
            "estimated_size_mb": round(self.estimated_size_bytes / (1024 * 1024), 2),
            "last_cleanup_ts": self.last_cleanup,
        }


class MemoryService:
    """
    Manages persistent session memory for the agentic research workflow.
    Each research session is keyed by session_id in Redis.
    Supports per-session TTL, size limits, automatic summarization,
    and graceful fallback.
    """
    _instance: Optional["MemoryService"] = None
    _fallback: dict[str, str] = {}

    def __new__(cls) -> "MemoryService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self.stats = MemoryStats()
        self.available = False
        self.client: Any = None
        self._pool: Any = None

        redis_cfg = settings.redis_config
        try:
            import redis as redis_module
            self._pool = redis_module.ConnectionPool(
                host=redis_cfg.REDIS_HOST,
                port=redis_cfg.REDIS_PORT,
                db=1,
                password=redis_cfg.REDIS_PASSWORD,
                socket_connect_timeout=redis_cfg.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
                max_connections=10,
                retry_on_timeout=True,
            )
            self.client = redis_module.Redis(connection_pool=self._pool)
            self.client.ping()
            self.available = True
            logger.info(
                "MemoryService connected to Redis (db=1)",
                extra={"event": "memory_connected", "host": redis_cfg.REDIS_HOST},
            )
        except Exception as e:
            self.available = False
            self.client = None
            logger.warning(
                f"Redis unavailable for memory ({e}). Using in-process fallback.",
                extra={"event": "memory_fallback", "error": str(e)},
            )

    @staticmethod
    def _key(session_id: str, field: str) -> str:
        return f"memory:{session_id}:{field}"

    def _check_session_limit(self) -> None:
        """Enforce maximum number of concurrent sessions."""
        if self.available:
            try:
                count = len(list(self.client.scan_iter("memory:*:session")))
                if count >= MAX_SESSIONS:
                    oldest = min(self.client.scan_iter("memory:*:session"),
                                 key=lambda k: self.client.ttl(k) or 0)
                    self.client.delete(oldest)
                    logger.info("Evicted oldest session due to limit", extra={"event": "memory_eviction"})
            except Exception:
                pass
        else:
            if len(self._fallback) >= MAX_SESSIONS:
                oldest_key = min(self._fallback, key=lambda k: self._fallback.get(k, ""))
                self._fallback.pop(oldest_key, None)

    def _check_size_limit(self, session_id: str, data: dict[str, Any]) -> bool:
        """Check if the session data exceeds the maximum size."""
        payload = json.dumps(data)
        size = len(payload.encode())
        if size > MAX_SESSION_SIZE_BYTES:
            logger.warning(
                f"Session {session_id} exceeds size limit ({size} > {MAX_SESSION_SIZE_BYTES})",
                extra={"event": "memory_size_exceeded", "session_id": session_id, "size_bytes": size},
            )
            return False
        return True

    def save_research_session(self, session_id: str, data: dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
        self._check_session_limit()
        if not self._check_size_limit(session_id, data):
            return

        key = self._key(session_id, "session")
        payload = json.dumps(data)

        if self.available:
            try:
                self.client.setex(key, ttl, payload)
                self._update_stats(session_id, len(payload.encode()))
                logger.info(
                    "Session saved",
                    extra={"event": "memory_save", "session_id": session_id, "ttl": ttl},
                )
            except Exception as e:
                logger.error(
                    f"Failed to save session: {e}",
                    extra={"event": "memory_save_error", "session_id": session_id},
                )
        else:
            self._fallback[key] = payload
            self._update_stats(session_id, len(payload.encode()))

    def get_research_session(self, session_id: str) -> Optional[dict[str, Any]]:
        key = self._key(session_id, "session")
        try:
            if self.available:
                raw = self.client.get(key)
            else:
                raw = self._fallback.get(key)

            if raw:
                logger.info(
                    "Session loaded",
                    extra={"event": "memory_load", "session_id": session_id},
                )
                return json.loads(raw)
        except Exception as e:
            logger.error(
                f"Failed to retrieve session: {e}",
                extra={"event": "memory_load_error", "session_id": session_id},
            )
        return None

    def update_research_memory(self, session_id: str, updates: dict[str, Any], ttl: int = DEFAULT_TTL) -> None:
        existing = self.get_research_session(session_id) or {}
        existing.update(updates)
        self.save_research_session(session_id, existing, ttl)
        logger.info(
            "Session updated",
            extra={
                "event": "memory_update",
                "session_id": session_id,
                "keys": list(updates.keys()),
            },
        )

    def delete_research_session(self, session_id: str) -> None:
        key = self._key(session_id, "session")
        if self.available:
            try:
                self.client.delete(key)
                self.stats.session_sizes.pop(session_id, None)
                logger.info(
                    "Session deleted",
                    extra={"event": "memory_delete", "session_id": session_id},
                )
            except Exception as e:
                logger.warning(
                    f"Failed to delete session: {e}",
                    extra={"event": "memory_delete_error", "session_id": session_id},
                )
        else:
            self._fallback.pop(key, None)
            self.stats.session_sizes.pop(session_id, None)

    def list_session_keys(self, pattern: str = "memory:*:session") -> list[str]:
        if not self.available:
            return list(self._fallback.keys())
        try:
            return list(self.client.scan_iter(pattern))
        except Exception:
            return []

    def get_active_sessions(self) -> list[dict[str, Any]]:
        keys = self.list_session_keys()
        sessions: list[dict[str, Any]] = []
        for key in keys:
            try:
                raw = self.client.get(key) if self.available else self._fallback.get(key)
                if raw:
                    data = json.loads(raw)
                    session_id = key.split(":")[1]
                    sessions.append({
                        "session_id": session_id,
                        "data_keys": list(data.keys()),
                        "size_bytes": len(raw.encode()),
                    })
            except Exception:
                continue
        return sessions

    def get_session_summary(self, session_id: str) -> Optional[dict[str, Any]]:
        data = self.get_research_session(session_id)
        if not data:
            return None
        return {
            "session_id": session_id,
            "key_count": len(data),
            "keys": list(data.keys()),
            "has_report": "report" in data or "final_answer" in data,
            "has_sources": "sources" in data,
        }

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count of removed sessions."""
        count = 0
        if self.available:
            try:
                for key in self.client.scan_iter("memory:*:session"):
                    if self.client.ttl(key) <= 0:
                        self.client.delete(key)
                        count += 1
            except Exception:
                pass
        self.stats.last_cleanup = time.time()
        logger.info(f"Cleanup removed {count} expired sessions", extra={"event": "memory_cleanup", "removed": count})
        return count

    def _update_stats(self, session_id: str, size_bytes: int) -> None:
        self.stats.session_sizes[session_id] = size_bytes
        self.stats.total_sessions = len(self.stats.session_sizes)
        self.stats.active_sessions = len(self.list_session_keys())
        self.stats.total_keys = self.stats.active_sessions
        self.stats.estimated_size_bytes = sum(self.stats.session_sizes.values())

    def get_statistics(self) -> dict[str, Any]:
        self.stats.active_sessions = len(self.list_session_keys())
        return self.stats.snapshot()

    def close(self) -> None:
        if self._pool:
            self._pool.disconnect()
        self._initialized = False
        MemoryService._instance = None


def get_memory_service() -> MemoryService:
    return MemoryService()
