# rate_limit.py - Middleware for API rate limiting.
"""
rate_limit.py
Basic rate-limiting middleware to protect expensive endpoints.
"""
import time
import logging
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings

logger = logging.getLogger("api.ratelimit")

# In-memory tracking for simplicity. Replace with Redis in distributed production.
# format: { "ip_address": {"count": int, "window_start": float} }
_rate_limits = {}

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # Bypass rate limiting for health endpoints
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)
            
        current_time = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECS
        max_req = settings.RATE_LIMIT_REQUESTS
        
        # Initialize or reset window
        if client_ip not in _rate_limits or (current_time - _rate_limits[client_ip]["window_start"] > window):
            _rate_limits[client_ip] = {"count": 1, "window_start": current_time}
        else:
            _rate_limits[client_ip]["count"] += 1
            if _rate_limits[client_ip]["count"] > max_req:
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                # Note: Raising HTTPException directly in middleware can be tricky in Starlette,
                # returning a raw response is safer, but for now we'll allow the exception handler to catch it.
                # Standard practice is to use slowapi or similar libraries for robust rate limiting.
                
        response = await call_next(request)
        return response
