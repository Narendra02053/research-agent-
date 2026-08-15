# session_service.py - Manages user sessions.
"""
session_service.py
Manages research session lifecycle: ID generation, status tracking,
and multi-step research continuation.
Designed to be future-ready for multi-user and distributed deployments.
"""

import uuid
import logging
import time
from typing import Optional
from app.core.memory import get_memory_service

logger = logging.getLogger(__name__)


class SessionService:
    def __init__(self):
        self.memory = get_memory_service()

    # ------------------------------------------------------------------ #
    #  Session creation                                                    #
    # ------------------------------------------------------------------ #
    def create_session(self, query: str) -> str:
        """
        Generate a unique session ID and persist initial metadata.
        Returns the session_id.
        """
        session_id = str(uuid.uuid4())
        self.memory.save_research_session(session_id, {
            "session_id": session_id,
            "query": query,
            "status": "created",
            "created_at": time.time(),
            "updated_at": time.time(),
            "research_steps": [],
            "report": None,
            "sources": []
        })
        logger.info(f"Session created [id={session_id}] query='{query[:60]}'")
        return session_id

    # ------------------------------------------------------------------ #
    #  Session retrieval                                                   #
    # ------------------------------------------------------------------ #
    def get_session(self, session_id: str) -> Optional[dict]:
        """Fetch full session data by ID."""
        session = self.memory.get_research_session(session_id)
        if not session:
            logger.warning(f"Session not found [id={session_id}]")
        return session

    # ------------------------------------------------------------------ #
    #  Status updates                                                      #
    # ------------------------------------------------------------------ #
    def mark_in_progress(self, session_id: str):
        self._update_status(session_id, "in_progress")

    def mark_complete(self, session_id: str, report: str, sources: list, steps: list, timing: dict):
        self.memory.update_research_memory(session_id, {
            "status": "complete",
            "report": report,
            "sources": sources,
            "research_steps": steps,
            "timing": timing,
            "updated_at": time.time()
        })
        logger.info(f"Session complete [id={session_id}]")

    def mark_failed(self, session_id: str, error: str):
        self.memory.update_research_memory(session_id, {
            "status": "failed",
            "error": error,
            "updated_at": time.time()
        })
        logger.error(f"Session failed   [id={session_id}] error='{error[:120]}'")

    def append_step(self, session_id: str, step: str):
        session = self.get_session(session_id)
        if session:
            steps = session.get("research_steps", [])
            steps.append(step)
            self.memory.update_research_memory(session_id, {
                "research_steps": steps,
                "updated_at": time.time()
            })

    # ------------------------------------------------------------------ #
    #  Internal helpers                                                    #
    # ------------------------------------------------------------------ #
    def _update_status(self, session_id: str, status: str):
        self.memory.update_research_memory(session_id, {
            "status": status,
            "updated_at": time.time()
        })
        logger.info(f"Session status → {status} [id={session_id}]")


def get_session_service() -> SessionService:
    return SessionService()
