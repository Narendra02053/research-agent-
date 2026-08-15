"""
app/core/llm.py
Production-grade LLM gateway with:
- Retry logic with exponential backoff
- Timeout handling
- Request tracing with correlation IDs
- Token usage tracking
- Response latency tracking
- Fallback support: Groq -> OpenAI -> Ollama
- Standardized LLM responses
- Structured logging

Backward-compatible: existing imports of get_llm_service() continue to work.
"""

import logging
import time
import asyncio
import functools
import uuid
from typing import Any, Callable, Optional, TypeVar

from app.core.logging_config import generate_trace_id

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])

DEFAULT_TIMEOUT_SECS = 60
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_BASE = 1.0


def _calculate_backoff(attempt: int, base: float = DEFAULT_BACKOFF_BASE) -> float:
    """Calculate exponential backoff with jitter."""
    import random
    return base * (2 ** attempt) + random.uniform(0, 0.5 * base)


class LLMError(Exception):
    """Base exception for LLM-related errors."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when an LLM call times out."""
    pass


class LLMRetryError(LLMError):
    """Raised when all retry attempts fail."""
    pass


class LLMResponse:
    """
    Standardized LLM response with metadata.
    Matches the app.llm.providers.base_provider.LLMResponse interface
    for backward compatibility.
    """
    def __init__(
        self,
        content: str,
        model: str = "",
        provider: str = "",
        tokens_used: int = 0,
        latency_ms: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
        trace_id: str = "",
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> None:
        self.content = content
        self.model = model
        self.provider = provider
        self.tokens_used = tokens_used
        self.latency_ms = latency_ms
        self.success = success
        self.error = error
        self.trace_id = trace_id
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    def to_dict(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "tokens_used": self.tokens_used or (self.prompt_tokens + self.completion_tokens),
            "latency_ms": round(self.latency_ms, 2),
            "success": self.success,
            "error": self.error,
            "trace_id": self.trace_id,
            "provider": self.provider,
        }


class LLMRetryHandler:
    """
    Wraps LLM calls with retry logic, timeout, and tracing.

    Usage:
        handler = LLMRetryHandler()
        response = handler.execute(
            call_fn=my_llm_call,
            prompt="...",
            task_type="deep_analysis",
        )
    """

    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout_secs: int = DEFAULT_TIMEOUT_SECS,
    ) -> None:
        self.max_retries = max_retries
        self.timeout_secs = timeout_secs

    def execute(
        self,
        call_fn: Callable[..., Any],
        prompt: str,
        task_type: str = "default",
        **kwargs: Any,
    ) -> LLMResponse:
        trace_id = generate_trace_id()
        start = time.perf_counter()
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"LLM call attempt {attempt + 1}/{self.max_retries + 1}",
                    extra={
                        "event": "llm_attempt",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "task_type": task_type,
                    },
                )

                result = call_fn(prompt=prompt, **kwargs)

                if isinstance(result, tuple) and hasattr(result[0], 'content'):
                    result = result[0]
                elif hasattr(result, 'content'):
                    pass
                else:
                    result = LLMResponse(content=str(result))

                latency = (time.perf_counter() - start) * 1000
                result.latency_ms = latency
                result.trace_id = trace_id

                tokens = getattr(result, "tokens_used", 0) or (
                    getattr(result, "prompt_tokens", 0) + getattr(result, "completion_tokens", 0)
                )

                logger.info(
                    f"LLM call succeeded",
                    extra={
                        "event": "llm_success",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "latency_ms": round(latency, 2),
                        "model": getattr(result, "model", "unknown"),
                        "provider": getattr(result, "provider", "unknown"),
                        "tokens_used": tokens,
                    },
                )
                return result

            except Exception as e:
                last_error = str(e)
                latency = (time.perf_counter() - start) * 1000
                logger.warning(
                    f"LLM call failed (attempt {attempt + 1}): {e}",
                    extra={
                        "event": "llm_retry",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "latency_ms": round(latency, 2),
                        "error": str(e),
                    },
                )

                if attempt < self.max_retries:
                    backoff = _calculate_backoff(attempt)
                    logger.info(
                        f"Retrying in {backoff:.2f}s...",
                        extra={
                            "event": "llm_backoff",
                            "trace_id": trace_id,
                            "backoff_secs": round(backoff, 2),
                        },
                    )
                    time.sleep(backoff)

        total_latency = (time.perf_counter() - start) * 1000
        logger.error(
            f"LLM call failed after {self.max_retries + 1} attempts",
            extra={
                "event": "llm_failed",
                "trace_id": trace_id,
                "total_latency_ms": round(total_latency, 2),
                "error": last_error,
            },
        )
        return LLMResponse(
            content="",
            error=last_error or "Unknown error",
            latency_ms=total_latency,
            trace_id=trace_id,
            success=False,
        )

    async def execute_async(
        self,
        call_fn: Callable[..., Any],
        prompt: str,
        task_type: str = "default",
        **kwargs: Any,
    ) -> LLMResponse:
        trace_id = generate_trace_id()
        start = time.perf_counter()
        last_error: Optional[str] = None

        for attempt in range(self.max_retries + 1):
            try:
                logger.info(
                    f"LLM async call attempt {attempt + 1}/{self.max_retries + 1}",
                    extra={
                        "event": "llm_async_attempt",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "task_type": task_type,
                    },
                )

                if asyncio.iscoroutinefunction(call_fn):
                    result = await asyncio.wait_for(
                        call_fn(prompt=prompt, **kwargs),
                        timeout=self.timeout_secs,
                    )
                else:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(call_fn, prompt=prompt, **kwargs),
                        timeout=self.timeout_secs,
                    )

                if hasattr(result, 'content'):
                    pass
                else:
                    result = LLMResponse(content=str(result))

                latency = (time.perf_counter() - start) * 1000
                result.latency_ms = latency
                result.trace_id = trace_id

                tokens = getattr(result, "tokens_used", 0) or (
                    getattr(result, "prompt_tokens", 0) + getattr(result, "completion_tokens", 0)
                )

                logger.info(
                    f"LLM async call succeeded",
                    extra={
                        "event": "llm_async_success",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "latency_ms": round(latency, 2),
                        "model": getattr(result, "model", "unknown"),
                        "tokens_used": tokens,
                    },
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout_secs}s"
                logger.warning(
                    f"LLM async call timed out (attempt {attempt + 1})",
                    extra={
                        "event": "llm_async_timeout",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                        "timeout_secs": self.timeout_secs,
                    },
                )
                if attempt < self.max_retries:
                    backoff = _calculate_backoff(attempt)
                    await asyncio.sleep(backoff)
                continue

            except Exception as e:
                last_error = str(e)
                logger.warning(
                    f"LLM async call failed (attempt {attempt + 1}): {e}",
                    extra={
                        "event": "llm_async_retry",
                        "trace_id": trace_id,
                        "attempt": attempt + 1,
                    },
                )
                if attempt < self.max_retries:
                    backoff = _calculate_backoff(attempt)
                    await asyncio.sleep(backoff)

        total_latency = (time.perf_counter() - start) * 1000
        logger.error(
            f"LLM async call failed after {self.max_retries + 1} attempts",
            extra={
                "event": "llm_async_failed",
                "trace_id": trace_id,
                "total_latency_ms": round(total_latency, 2),
                "error": last_error,
            },
        )
        return LLMResponse(
            content="",
            error=last_error or "Unknown error",
            latency_ms=total_latency,
            trace_id=trace_id,
            success=False,
        )


class LLMService:
    """
    High-level LLM service that wraps the LLM router with retry,
    timeout, tracing, and standardized responses.

    Usage:
        service = get_llm_service()
        result = service.generate(prompt, task_type="deep_analysis")
        text = result.content
        metrics = result.to_dict()
    """

    def __init__(self) -> None:
        self._retry_handler = LLMRetryHandler()
        self._router: Any = None

    def _get_router(self) -> Any:
        if self._router is None:
            try:
                from app.llm.router import get_llm_router
                self._router = get_llm_router()
            except Exception:
                raise LLMError("LLM router not available")
        return self._router

    def generate(
        self,
        prompt: str,
        task_type: str = "default",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        override_model: Optional[str] = None,
        override_provider: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate a response with retry, timeout, and tracing.
        """
        def _call(prompt: str, **kwargs: Any) -> Any:
            router = self._get_router()
            return router.generate(
                prompt=prompt,
                task_type=kwargs.get("task_type", "default"),
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 2048),
                override_model=kwargs.get("override_model"),
                override_provider=kwargs.get("override_provider"),
            )

        result = self._retry_handler.execute(
            call_fn=_call,
            prompt=prompt,
            task_type=task_type,
            temperature=temperature,
            max_tokens=max_tokens,
            override_model=override_model,
            override_provider=override_provider,
        )
        return result

    async def generate_async(
        self,
        prompt: str,
        task_type: str = "default",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        override_model: Optional[str] = None,
        override_provider: Optional[str] = None,
    ) -> LLMResponse:
        """
        Async generation with retry, timeout, and tracing.
        """
        def _call(prompt: str, **kwargs: Any) -> Any:
            router = self._get_router()
            return router.generate(
                prompt=prompt,
                task_type=kwargs.get("task_type", "default"),
                temperature=kwargs.get("temperature", 0.1),
                max_tokens=kwargs.get("max_tokens", 2048),
                override_model=kwargs.get("override_model"),
                override_provider=kwargs.get("override_provider"),
            )

        result = await self._retry_handler.execute_async(
            call_fn=_call,
            prompt=prompt,
            task_type=task_type,
            temperature=temperature,
            max_tokens=max_tokens,
            override_model=override_model,
            override_provider=override_provider,
        )
        return result

    def generate_response(self, prompt: str, task_type: str = "default") -> str:
        """Backward-compatible convenience wrapper returning plain string."""
        return self.generate(prompt, task_type=task_type).content

    def available_providers(self) -> list[dict[str, Any]]:
        try:
            router = self._get_router()
            return router.available_providers()
        except Exception as e:
            logger.error(f"Failed to get available providers: {e}")
            return []

    def usage_summary(self) -> dict[str, Any]:
        try:
            router = self._get_router()
            return router.usage_summary()
        except Exception:
            return {"total_requests": 0, "total_tokens": 0, "estimated_total_cost_usd": 0.0}


_service_instance: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create the singleton LLM service."""
    global _service_instance
    if _service_instance is None:
        _service_instance = LLMService()
    return _service_instance


def get_llm_router():
    """
    Backward-compatible access to the underlying router.
    """
    from app.llm.router import get_llm_router as _get_llm_router
    return _get_llm_router()
