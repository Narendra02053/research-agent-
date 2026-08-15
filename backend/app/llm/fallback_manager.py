# fallback_manager.py - Manages fallback logic for LLM providers.
"""
fallback_manager.py
Executes an LLM request through an ordered chain of providers,
automatically falling back when one fails.
"""
import logging
from typing import Optional
from app.llm.providers.base_provider import BaseLLMProvider, LLMResponse

logger = logging.getLogger(__name__)


class FallbackManager:
    """
    Given an ordered list of providers, tries each one in sequence until
    a successful response is produced.
    """

    def execute(
        self,
        providers: list[BaseLLMProvider],
        prompt: str,
        models: Optional[list[Optional[str]]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        task_type: str = "",
    ) -> LLMResponse:
        """
        Try providers in priority order. Return first successful response.
        Raises RuntimeError if all providers fail.
        """
        if models is None:
            models = [None] * len(providers)

        last_error = None
        for provider, model in zip(providers, models):
            if not provider.is_available():
                logger.info(f"[Fallback] Skipping '{provider.name}' — not available.")
                continue

            logger.info(f"[Fallback] Trying provider='{provider.name}' model='{model}' for task='{task_type}'")
            response = provider.generate(prompt, model=model, temperature=temperature, max_tokens=max_tokens)

            if response.success:
                return response

            logger.warning(
                f"[Fallback] Provider '{provider.name}' failed: {response.error}. "
                f"Trying next in chain..."
            )
            last_error = response.error

        raise RuntimeError(
            f"All LLM providers failed for task '{task_type}'. Last error: {last_error}"
        )
