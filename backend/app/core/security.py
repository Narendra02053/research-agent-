"""
security.py
Security foundations for the API.
Prepared for API key authentication and secure headers.
"""
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

# Define API key header
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

# Dummy verification function for future implementation
async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Placeholder for API key verification logic.
    Currently allows all requests for development.
    """
    if settings.ENVIRONMENT == "production":
        # In production, actually verify the key against a database/cache
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key missing"
            )
        # Dummy check
        if api_key != "super_secret_production_key":
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API Key"
            )
    return api_key
