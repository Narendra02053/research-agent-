"""
history_service.py
Maintains a chronological research history with citations and metadata.
Designed for future dashboard/analytics usage and cross-session retrieval.
"""

import time
import logging
from typing import List, Optional
from app.core.memory import get_memory_service

logger = logging.getLogger(__name__)

HISTORY_KEY = "research:global_history"

class HistoryService:
    def __init__(self):
        self.memory = get_memory_service()

    # ------------------------------------------------------------------ #
    #  Append a completed session to history                              #
    # ------------------------------------------------------------------ #
    def record_session(
        self,
        session_id: str,
        query: str,
        report_summary: str,
        sources: List[dict],
        timing: dict
    ):
        """
        Append a research session entry to the global history log.
        Stores in Redis sorted set ordered by timestamp.
        """
        entry = {
            "session_id": session_id,
            "query": query,
            "report_summary": report_summary[:500],   # Truncate for storage
            "sources": sources,
            "timing": timing,
            "recorded_at": time.time()
        }

        # Store individual session record
        self.memory.save_research_session(f"history:{session_id}", entry, ttl=604800)   # 7 days

        # Append session_id to global sorted list
        if self.memory.available:
            try:
                self.memory.client.zadd(HISTORY_KEY, {session_id: time.time()})
                logger.info(f"History recorded [session={session_id}]")
            except Exception as e:
                logger.warning(f"Failed to update global history index: {e}")

    # ------------------------------------------------------------------ #
    #  Retrieve history                                                   #
    # ------------------------------------------------------------------ #
    def get_recent_sessions(self, limit: int = 10) -> List[dict]:
        """Return the N most recently completed research sessions."""
        sessions = []
        if self.memory.available:
            try:
                # Get the most recent session IDs by score (timestamp), descending
                session_ids = self.memory.client.zrevrange(HISTORY_KEY, 0, limit - 1)
                for sid in session_ids:
                    record = self.memory.get_research_session(f"history:{sid}")
                    if record:
                        sessions.append(record)
            except Exception as e:
                logger.warning(f"Failed to retrieve history: {e}")
        else:
            logger.info("Redis not available; history retrieval is disabled in fallback mode.")
        return sessions

    def get_session_record(self, session_id: str) -> Optional[dict]:
        """Retrieve a specific historical session record by ID."""
        return self.memory.get_research_session(f"history:{session_id}")

    def get_history_count(self) -> int:
        """Total number of completed research sessions tracked."""
        if self.memory.available:
            try:
                return self.memory.client.zcard(HISTORY_KEY)
            except Exception:
                pass
        return 0


def get_history_service() -> HistoryService:
    return HistoryService()
