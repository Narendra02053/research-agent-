"""
groq_provider.py
LLM provider implementation for Groq Cloud (Llama models).
"""
import os
import logging
from typing import Optional
from langchain_groq import ChatGroq
from app.llm.providers.base_provider import BaseLLMProvider, LLMResponse, ProviderConfig

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
FAST_MODEL = "llama3-8b-8192"


class GroqProvider(BaseLLMProvider):

    def __init__(self):
        config = ProviderConfig(
            name="groq",
            models=[DEFAULT_MODEL, FAST_MODEL, "llama3-70b-8192"],
            priority=0,   # Highest priority — fast + free tier
        )
        super().__init__(config)
        self._api_key = os.getenv("GROQ_API_KEY", "")
        self._clients: dict[str, ChatGroq] = {}

    def is_available(self) -> bool:
        return bool(self._api_key and self._api_key != "your_key_here")

    def _get_client(self, model: str, temperature: float, max_tokens: int) -> ChatGroq:
        key = f"{model}:{temperature}:{max_tokens}"
        if key not in self._clients:
            self._clients[key] = ChatGroq(
                model=model,
                api_key=self._api_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        return self._clients[key]

    def generate(self, prompt: str, model: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 2048) -> LLMResponse:
        model = model or DEFAULT_MODEL

        def _inner():
            client = self._get_client(model, temperature, max_tokens)
            response = client.invoke(prompt)
            content = response.content
            usage = getattr(response, "response_metadata", {}).get("token_usage", {})
            return LLMResponse(
                content=content,
                provider=self.name,
                model=model,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                success=True,
            )

        return self._timed_generate(_inner)
