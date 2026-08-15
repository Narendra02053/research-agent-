# model_registry.py - Registry of available LLM models.
"""
model_registry.py
Central registry of all models, their capabilities, token limits and pricing.
Used by LLMRouter to select the best model for a given task.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelMeta:
    provider: str
    model_id: str
    context_window: int             # Max input tokens
    max_output_tokens: int
    cost_per_1k_input: float        # USD
    cost_per_1k_output: float       # USD
    capabilities: list              # e.g. ["reasoning", "fast", "coding"]
    notes: str = ""


# ------------------------------------------------------------------ #
#  Registry                                                            #
# ------------------------------------------------------------------ #
MODEL_REGISTRY: dict[str, ModelMeta] = {
    # Groq
    "groq:llama-3.3-70b-versatile": ModelMeta(
        provider="groq",
        model_id="llama-3.3-70b-versatile",
        context_window=128_000,
        max_output_tokens=32_768,
        cost_per_1k_input=0.0,      # Free tier
        cost_per_1k_output=0.0,
        capabilities=["reasoning", "deep_analysis", "report_generation", "evaluation"],
        notes="Primary model. Best quality on Groq.",
    ),
    "groq:llama-3.1-8b-instant": ModelMeta(
        provider="groq",
        model_id="llama-3.1-8b-instant",
        context_window=128_000,
        max_output_tokens=8_192,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        capabilities=["fast", "planning", "classification"],
        notes="Lightweight; ideal for planning & classification tasks.",
    ),
    # OpenAI
    "openai:gpt-4o-mini": ModelMeta(
        provider="openai",
        model_id="gpt-4o-mini",
        context_window=128_000,
        max_output_tokens=16_384,
        cost_per_1k_input=0.00015,
        cost_per_1k_output=0.0006,
        capabilities=["reasoning", "fast", "coding", "report_generation"],
        notes="Cost-effective OpenAI fallback.",
    ),
    "openai:gpt-4o": ModelMeta(
        provider="openai",
        model_id="gpt-4o",
        context_window=128_000,
        max_output_tokens=16_384,
        cost_per_1k_input=0.005,
        cost_per_1k_output=0.015,
        capabilities=["deep_analysis", "reasoning", "evaluation", "multimodal"],
        notes="Highest quality; use only for premium tasks.",
    ),
    # Ollama (local)
    "ollama:llama3": ModelMeta(
        provider="ollama",
        model_id="llama3",
        context_window=8_192,
        max_output_tokens=4_096,
        cost_per_1k_input=0.0,
        cost_per_1k_output=0.0,
        capabilities=["offline", "fast", "planning"],
        notes="Local fallback. Requires Ollama to be running.",
    ),
}


# ------------------------------------------------------------------ #
#  Task → Model mapping                                                #
# ------------------------------------------------------------------ #
TASK_MODEL_MAP: dict[str, list[str]] = {
    "planning":          ["groq:llama-3.1-8b-instant",        "openai:gpt-4o-mini",  "ollama:llama3"],
    "fast_reasoning":    ["groq:llama-3.1-8b-instant",        "openai:gpt-4o-mini",  "ollama:llama3"],
    "deep_analysis":     ["groq:llama-3.3-70b-versatile","openai:gpt-4o-mini", "ollama:llama3"],
    "report_generation": ["groq:llama-3.3-70b-versatile","openai:gpt-4o-mini", "ollama:llama3"],
    "evaluation":        ["groq:llama-3.3-70b-versatile","openai:gpt-4o-mini", "ollama:llama3"],
    "hallucination":     ["groq:llama-3.3-70b-versatile","openai:gpt-4o",      "ollama:llama3"],
    "default":           ["groq:llama-3.3-70b-versatile","openai:gpt-4o-mini", "ollama:llama3"],
}


def get_model_chain(task_type: str) -> list[ModelMeta]:
    """Return ordered list of ModelMeta objects for a given task type."""
    keys = TASK_MODEL_MAP.get(task_type, TASK_MODEL_MAP["default"])
    return [MODEL_REGISTRY[k] for k in keys if k in MODEL_REGISTRY]
