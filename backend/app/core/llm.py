"""
app/core/llm.py
Backward-compatibility shim.
All code that previously imported get_llm_service() from here
will now transparently use the new multi-provider LLM gateway.
"""
from app.llm.router import get_llm_router, get_llm_service  # noqa: F401

__all__ = ["get_llm_service", "get_llm_router"]
