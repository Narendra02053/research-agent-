"""
request_logging.py
Middleware for logging incoming HTTP requests and execution timing.
"""
import time
import uuid
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("api.request")

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.perf_counter()
        
        # Log incoming request
        logger.info(f"[{request_id}] Started {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            process_time = time.perf_counter() - start_time
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request_id
            
            logger.info(f"[{request_id}] Completed {response.status_code} in {process_time:.3f}s")
            
            return response
        except Exception as exc:
            process_time = time.perf_counter() - start_time
            logger.error(f"[{request_id}] Failed with exception in {process_time:.3f}s: {str(exc)}")
            raise
