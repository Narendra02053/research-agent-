# token_monitor.py - Monitors LLM token usage and limits.
"""
token_monitor.py
Tracks per-request token usage and estimates cost.
"""
import logging
from app.llm.providers.base_provider import LLMResponse
from app.llm.model_registry import MODEL_REGISTRY

logger = logging.getLogger(__name__)


class TokenMonitor:
    """
    Singleton that logs token usage and computes estimated cost after each
    LLM call. Future-ready for pushing metrics to Prometheus.
    """
    _instance = None
    _total_tokens: int = 0
    _total_cost: float = 0.0
    _total_requests: int = 0

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def record(self, response: LLMResponse, task_type: str = ""):
        """Call this after every LLM response."""
        registry_key = f"{response.provider}:{response.model}"
        meta = MODEL_REGISTRY.get(registry_key)

        input_cost = output_cost = 0.0
        if meta:
            input_cost  = (response.prompt_tokens     / 1000) * meta.cost_per_1k_input
            output_cost = (response.completion_tokens  / 1000) * meta.cost_per_1k_output

        total_cost = input_cost + output_cost
        total_tokens = response.prompt_tokens + response.completion_tokens

        self._total_tokens   += total_tokens
        self._total_cost     += total_cost
        self._total_requests += 1

        logger.info(
            f"[TokenMonitor] task={task_type or 'n/a'} "
            f"provider={response.provider} model={response.model} "
            f"tokens={total_tokens} (in={response.prompt_tokens}, out={response.completion_tokens}) "
            f"latency={response.latency_ms:.0f}ms "
            f"cost=${total_cost:.6f}"
        )

    def summary(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_tokens": self._total_tokens,
            "estimated_total_cost_usd": round(self._total_cost, 6),
        }


def get_token_monitor() -> TokenMonitor:
    return TokenMonitor()
