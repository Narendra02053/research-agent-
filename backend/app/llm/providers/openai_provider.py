"""
openai_provider.py
LLM provider implementation for OpenAI GPT models.
"""
import os
import logging
from typing import Optional
from app.llm.providers.base_provider import BaseLLMProvider, LLMResponse, ProviderConfig

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAIProvider(BaseLLMProvider):

    def __init__(self):
        config = ProviderConfig(
            name="openai",
            models=["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
            priority=1,
        )
        super().__init__(config)
        self._api_key = os.getenv("OPENAI_API_KEY", "")

    def is_available(self) -> bool:
        return bool(self._api_key and not self._api_key.startswith("your"))

    def generate(self, prompt: str, model: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 2048) -> LLMResponse:
        model = model or DEFAULT_MODEL

        def _inner():
            # Lazy import so the app starts fine without openai installed
            try:
                from langchain_openai import ChatOpenAI
            except ImportError:
                raise RuntimeError("langchain_openai package is not installed. Run: pip install langchain-openai")

            client = ChatOpenAI(
                model=model,
                api_key=self._api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            response = client.invoke(prompt)
            usage = getattr(response, "response_metadata", {}).get("token_usage", {})
            return LLMResponse(
                content=response.content,
                provider=self.name,
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                success=True,
            )

        return self._timed_generate(_inner)
