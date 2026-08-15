"""
memory.py
Research session memory backed by Redis.
Stores agent outputs, intermediate state snapshots, and final reports
so the system can recall previous context across API calls.
"""

import os
import json
import logging
import redis
from typing import Optional

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Manages persistent session memory for the agentic research workflow.
    Each research session is keyed by session_id in Redis.
    Falls back gracefully to in-process dict when Redis is unavailable.
    """
    _instance = None
    _fallback: dict = {}   # In-memory fallback store

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            host = os.getenv("REDIS_HOST", "localhost")
            port = int(os.getenv("REDIS_PORT", 6379))
            try:
                cls._instance.client = redis.Redis(
                    host=host, port=port, db=1, decode_responses=True,
                    socket_connect_timeout=2
                )
                cls._instance.client.ping()
                cls._instance.available = True
                logger.info("MemoryService connected to Redis (db=1).")
            except Exception as e:
                cls._instance.available = False
                cls._instance.client = None
                logger.warning(f"Redis unavailable for memory ({e}). Using in-process fallback.")
        return cls._instance

    # ------------------------------------------------------------------ #
    #  Session key builder                                                 #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _key(session_id: str, field: str) -> str:
        return f"memory:{session_id}:{field}"

    # ------------------------------------------------------------------ #
    #  Core memory operations                                             #
    # ------------------------------------------------------------------ #
    def save_research_session(self, session_id: str, data: dict, ttl: int = 86400):
        """
        Persist a full research session snapshot under session_id.
        Default TTL: 24 hours.
        """
        key = self._key(session_id, "session")
        payload = json.dumps(data)
        if self.available:
            try:
                self.client.setex(key, ttl, payload)
                logger.info(f"Session saved   [id={session_id}]")
            except Exception as e:
                logger.error(f"Failed to save session: {e}")
        else:
            self._fallback[key] = payload

    def get_research_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve a research session snapshot by session_id.
        Returns None if not found.
        """
        key = self._key(session_id, "session")
        try:
            if self.available:
                raw = self.client.get(key)
            else:
                raw = self._fallback.get(key)
            if raw:
                logger.info(f"Session loaded  [id={session_id}]")
                return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to retrieve session: {e}")
        return None

    def update_research_memory(self, session_id: str, updates: dict, ttl: int = 86400):
        """
        Merge new data into an existing session, or create it if missing.
        Useful for updating intermediate agent outputs mid-workflow.
        """
        existing = self.get_research_session(session_id) or {}
        existing.update(updates)
        self.save_research_session(session_id, existing, ttl)
        logger.info(f"Session updated [id={session_id}]  keys={list(updates.keys())}")

    def delete_research_session(self, session_id: str):
        """Remove a session from memory."""
        key = self._key(session_id, "session")
        if self.available:
            try:
                self.client.delete(key)
                logger.info(f"Session deleted [id={session_id}]")
            except Exception as e:
                logger.warning(f"Failed to delete session: {e}")
        else:
            self._fallback.pop(key, None)

    def list_session_keys(self, pattern: str = "memory:*:session") -> list:
        """List all session IDs currently in memory (Redis only)."""
        if not self.available:
            return list(self._fallback.keys())
        try:
            return list(self.client.scan_iter(pattern))
        except Exception:
            return []


def get_memory_service() -> MemoryService:
    return MemoryService()
