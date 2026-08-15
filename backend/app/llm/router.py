# router.py - Routes LLM requests to appropriate providers.
"""
router.py
Central LLM gateway — single entry point for all LLM calls in the platform.
Selects the correct model chain, runs through the fallback manager,
and records token usage.
"""
import logging
from typing import Optional
from app.llm.providers.base_provider import LLMResponse
from app.llm.providers.groq_provider import GroqProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.ollama_provider import OllamaProvider
from app.llm.model_registry import get_model_chain
from app.llm.fallback_manager import FallbackManager
from app.llm.token_monitor import get_token_monitor

logger = logging.getLogger(__name__)

# Provider singletons — instantiated once at module load
_PROVIDERS = {
    "groq":   GroqProvider(),
    "openai": OpenAIProvider(),
    "ollama": OllamaProvider(),
}


class LLMRouter:
    """
    Drop-in replacement for the old LLMService.
    Usage:
        router = get_llm_router()
        result = router.generate(prompt, task_type="deep_analysis")
        text   = result.content
    """

    def __init__(self):
        self._fallback = FallbackManager()
        self._monitor  = get_token_monitor()

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
        Route the prompt through the best available model chain for the
        given task_type, applying fallback automatically.
        Calls are wrapped in a Phoenix / OTEL span for observability.
        """
        model_chain = get_model_chain(task_type)

        providers_ordered = []
        models_ordered    = []

        for meta in model_chain:
            provider = _PROVIDERS.get(meta.provider)
            if provider:
                providers_ordered.append(provider)
                models_ordered.append(override_model or meta.model_id)

        # Optional: force a specific provider/model (e.g., from API request)
        if override_provider and override_provider in _PROVIDERS:
            providers_ordered = [_PROVIDERS[override_provider]] + providers_ordered
            models_ordered    = [override_model] + models_ordered

        # ── Phoenix instrumentation ──────────────────────────────────────
        from app.observability.llm_instrumentation import instrument_llm_call

        def _inner_generate(**kw):
            return self._fallback.execute(
                providers=providers_ordered,
                prompt=prompt,
                models=models_ordered,
                temperature=kw.get("temperature", temperature),
                max_tokens=kw.get("max_tokens", max_tokens),
                task_type=task_type,
            )

        response = instrument_llm_call(
            _inner_generate,
            prompt=prompt,
            task_type=task_type,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        # ────────────────────────────────────────────────────────────────

        self._monitor.record(response, task_type=task_type)
        return response


    # Convenience wrapper — returns plain string to keep backward compat
    def generate_response(self, prompt: str, task_type: str = "default") -> str:
        return self.generate(prompt, task_type=task_type).content

    def available_providers(self) -> list[dict]:
        return [
            {
                "name": name,
                "available": p.is_available(),
                "models": p.config.models,
                "priority": p.config.priority,
            }
            for name, p in _PROVIDERS.items()
        ]

    def usage_summary(self) -> dict:
        return self._monitor.summary()


# ------------------------------------------------------------------ #
#  Singleton accessor                                                  #
# ------------------------------------------------------------------ #
_router_instance: Optional[LLMRouter] = None


def get_llm_router() -> LLMRouter:
    global _router_instance
    if _router_instance is None:
        _router_instance = LLMRouter()
    return _router_instance


# Backward-compat shim so existing code that calls get_llm_service() still works
def get_llm_service():
    return get_llm_router()
