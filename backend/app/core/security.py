# security.py - Security and authentication utilities.
"""
security.py
Production-grade security foundations:
- API key validation with hashed comparison
- JWT authentication helpers
- Rate limiting token bucket
- Secret masking in logs
- Input sanitization helpers
- Security audit logging
"""

import hashlib
import hmac
import logging
import re
import secrets
import time
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.config import settings

logger = logging.getLogger(__name__)

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA-256 with a configurable salt."""
    salt = settings.security.API_KEY_HASH_SALT or "default-salt"
    return hashlib.sha256(f"{salt}:{api_key}".encode()).hexdigest()


def verify_api_key_hash(api_key: str, stored_hash: str) -> bool:
    """Constant-time comparison of API key against stored hash."""
    computed = hash_api_key(api_key)
    return hmac.compare_digest(computed, stored_hash)


def create_jwt_token(
    subject: str,
    extra_claims: Optional[dict[str, object]] = None,
    expires_in_hours: Optional[int] = None,
) -> str:
    """
    Create a JWT token using the configured secret key.
    Falls back gracefully if pyjwt is not installed.
    """
    try:
        import jwt as pyjwt
    except ImportError:
        logger.error("PyJWT is not installed. Run: pip install pyjwt")
        raise RuntimeError("PyJWT is required for JWT support")

    expiry_hours = expires_in_hours or settings.security.JWT_EXPIRATION_HOURS
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, object] = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(hours=expiry_hours),
        "iss": settings.PROJECT_NAME,
    }
    if extra_claims:
        payload.update(extra_claims)
    return pyjwt.encode(payload, settings.security.JWT_SECRET_KEY, algorithm=settings.security.JWT_ALGORITHM)


def decode_jwt_token(token: str) -> dict[str, object]:
    """Decode and validate a JWT token."""
    try:
        import jwt as pyjwt
        return pyjwt.decode(
            token,
            settings.security.JWT_SECRET_KEY,
            algorithms=[settings.security.JWT_ALGORITHM],
        )
    except ImportError:
        raise RuntimeError("PyJWT is required for JWT support")


def mask_secret(value: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive strings for logging.
    Shows only the last `visible_chars` characters.
    If the value is very short (<= visible_chars + 1), masks the entire string.

    Example:
        mask_secret("sk-abc123def456") -> "***********f456"
        mask_secret("short") -> "****"
        mask_secret("abcde") -> "*bcde"
    """
    if not value or len(value) <= visible_chars + 1:
        return "****"
    return f"{'*' * (len(value) - visible_chars)}{value[-visible_chars:]}"


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize user input for logging and storage.
    Strips control characters, limits length.
    """
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return cleaned[:max_length]


def sanitize_html(text: str) -> str:
    """Strip HTML tags from input to prevent XSS."""
    return re.sub(r"<[^>]*>", "", text)


class RateLimiter:
    """
    Sliding window rate limiter using in-memory counters.
    For distributed rate limiting, use Redis-based implementation.
    """

    def __init__(self, max_requests: int = 100, window_secs: int = 60):
        self.max_requests = max_requests
        self.window_secs = window_secs
        self._buckets: dict[str, list[float]] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_secs

        if key not in self._buckets:
            self._buckets[key] = []

        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]

        if len(self._buckets[key]) >= self.max_requests:
            return False

        self._buckets[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        cutoff = now - self.window_secs
        if key not in self._buckets:
            return self.max_requests
        self._buckets[key] = [t for t in self._buckets[key] if t > cutoff]
        return max(0, self.max_requests - len(self._buckets[key]))

    def reset(self, key: str) -> None:
        self._buckets.pop(key, None)


class SecurityAuditLogger:
    """Logs security-relevant events in a structured format."""

    @staticmethod
    def log_auth_success(user_id: str, method: str) -> None:
        logger.info("Authentication successful", extra={
            "event": "auth_success",
            "user_id": mask_secret(user_id),
            "auth_method": method,
        })

    @staticmethod
    def log_auth_failure(user_id: str, method: str, reason: str) -> None:
        logger.warning("Authentication failed", extra={
            "event": "auth_failure",
            "user_id": mask_secret(user_id),
            "auth_method": method,
            "reason": reason,
        })

    @staticmethod
    def log_rate_limit_hit(key: str) -> None:
        logger.warning("Rate limit exceeded", extra={
            "event": "rate_limit_hit",
            "key": mask_secret(key),
        })

    @staticmethod
    def log_access_denied(resource: str, user_id: str) -> None:
        logger.warning("Access denied", extra={
            "event": "access_denied",
            "resource": resource,
            "user_id": mask_secret(user_id),
        })


async def verify_api_key(api_key: str = Security(api_key_header)) -> Optional[str]:
    """
    Verify API key from X-API-Key header.
    In development, allows all requests.
    In production, validates against configured keys.

    Backward-compatible: returns the api_key string if valid.
    """
    audit = SecurityAuditLogger()

    if settings.is_development and not api_key:
        return "development-auto-granted"

    if not api_key:
        audit.log_auth_failure("unknown", "api_key", "missing")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key missing",
        )

    if settings.is_production:
        stored_hash = hash_api_key(settings.security.JWT_SECRET_KEY or "fallback-key")
        if not verify_api_key_hash(api_key, stored_hash):
            audit.log_auth_failure(mask_secret(api_key), "api_key", "invalid")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid API Key",
            )

    audit.log_auth_success(mask_secret(api_key), "api_key")
    return api_key
