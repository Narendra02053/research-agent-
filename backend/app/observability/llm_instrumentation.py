"""
llm_instrumentation.py
─────────────────────────────────────────────────────────────────
Manual Phoenix spans wrapping the LLMRouter.generate() call.

The LangChain auto-instrumentation already captures most chain-level
traces, but this module adds finer-grained spans that record:
  • task_type, provider, model selected
  • prompt length (tokens approximation)
  • response length and latency
  • whether fallback was triggered
  • errors and retry counts

Usage (already integrated in llm/router.py via `instrument_llm_call`):
    from app.observability.llm_instrumentation import instrument_llm_call
    response = instrument_llm_call(router_fn, prompt, task_type, ...)
"""

import logging
import time
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


def instrument_llm_call(
    generate_fn: Callable,
    prompt: str,
    task_type: str = "default",
    temperature: float = 0.1,
    max_tokens: int = 2048,
    **kwargs: Any,
) -> Any:
    """
    Wrap an LLMRouter.generate() call inside a Phoenix / OTEL span.

    Args:
        generate_fn: The bound LLMRouter.generate method
        prompt: The full prompt string
        task_type: Research task type (planning / deep_analysis / etc.)
        temperature, max_tokens: LLM parameters

    Returns:
        LLMResponse from the underlying generate call
    """
    from app.observability.phoenix_tracer import phoenix_span

    attrs = {
        "llm.task_type": task_type,
        "llm.temperature": temperature,
        "llm.max_tokens": max_tokens,
        "llm.prompt_length": len(prompt),
        "llm.prompt_preview": prompt[:200],
    }

    with phoenix_span(f"llm.generate.{task_type}", attrs, span_kind="LLM") as span:
        t0 = time.perf_counter()
        try:
            response = generate_fn(
                prompt=prompt,
                task_type=task_type,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000

            # Enrich span with response metadata
            span.set_attribute("llm.provider", getattr(response, "provider", "unknown"))
            span.set_attribute("llm.model", getattr(response, "model", "unknown"))
            span.set_attribute("llm.latency_ms", round(elapsed_ms, 1))
            span.set_attribute("llm.response_length", len(getattr(response, "content", "")))
            span.set_attribute("llm.success", getattr(response, "success", True))
            span.set_attribute("llm.prompt_tokens", getattr(response, "prompt_tokens", 0))
            span.set_attribute("llm.completion_tokens", getattr(response, "completion_tokens", 0))

            if not getattr(response, "success", True):
                span.set_attribute("llm.error", getattr(response, "error", "unknown"))

            return response
        except Exception as exc:
            span.set_attribute("llm.error", str(exc))
            raise


def trace_agent_node(node_name: str, state_keys_to_log: Optional[list] = None):
    """
    Decorator factory for wrapping a LangGraph agent node function
    in a Phoenix span.

    Usage:
        @trace_agent_node("retrieval_agent", ["query", "sources"])
        def retrieval_node(state):
            ...
    """
    def decorator(fn: Callable) -> Callable:
        def wrapper(state: dict, *args, **kwargs):
            from app.observability.phoenix_tracer import phoenix_span
            attrs = {"agent.node": node_name}
            if state_keys_to_log:
                for k in state_keys_to_log:
                    val = state.get(k, "")
                    if isinstance(val, str):
                        attrs[f"agent.{k}"] = val[:300]
                    elif isinstance(val, list):
                        attrs[f"agent.{k}_count"] = len(val)
            with phoenix_span(f"agent.{node_name}", attrs, span_kind="CHAIN"):
                return fn(state, *args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator
