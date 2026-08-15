"""
base_provider.py
Abstract base class for all LLM providers.
All providers must implement generate() and optionally stream().
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator, Optional
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class ProviderConfig:
    name: str
    models: list
    enabled: bool = True
    priority: int = 0          # Lower = higher priority
    extra: dict = field(default_factory=dict)


class BaseLLMProvider(ABC):
    """
    Unified interface every LLM provider must implement.
    """

    def __init__(self, config: ProviderConfig):
        self.config = config
        self.name = config.name

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the provider can currently handle requests."""

    @abstractmethod
    def generate(self, prompt: str, model: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 2048) -> LLMResponse:
        """Synchronous generation — returns a complete LLMResponse."""

    # Optional streaming — providers may override
    async def stream(self, prompt: str, model: Optional[str] = None,
                     temperature: float = 0.1) -> AsyncGenerator[str, None]:
        """Async token-by-token streaming. Falls back to single-shot by default."""
        response = self.generate(prompt, model=model, temperature=temperature)
        yield response.content

    def _timed_generate(self, fn, *args, **kwargs) -> LLMResponse:
        """Helper that wraps any generation function with latency tracking."""
        t0 = time.time()
        try:
            result: LLMResponse = fn(*args, **kwargs)
            result.latency_ms = (time.time() - t0) * 1000
            return result
        except Exception as e:
            latency = (time.time() - t0) * 1000
            logger.error(f"[{self.name}] generation failed after {latency:.0f}ms: {e}")
            return LLMResponse(
                content="",
                provider=self.name,
                model=kwargs.get("model", "unknown"),
                latency_ms=latency,
                success=False,
                error=str(e),
            )
