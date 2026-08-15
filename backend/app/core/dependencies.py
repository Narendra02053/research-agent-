"""
dependencies.py
Dependency injection definitions for reusable services and clients.
"""
from fastapi import Depends
from app.core.config import settings, Settings
from app.core.security import verify_api_key

# ------------------------------------------------------------------ #
#  Settings Dependency                                                 #
# ------------------------------------------------------------------ #
def get_settings() -> Settings:
    """Dependency to inject global settings."""
    return settings

# ------------------------------------------------------------------ #
#  Security Dependency                                                 #
# ------------------------------------------------------------------ #
def require_auth(api_key: str = Depends(verify_api_key)):
    """Dependency to require authentication."""
    return api_key
