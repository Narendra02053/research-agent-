"""
ollama_provider.py
Local Ollama provider — no API key required.
Acts as last-resort offline fallback.
"""
import os
import logging
import requests
from typing import Optional
from app.llm.providers.base_provider import BaseLLMProvider, LLMResponse, ProviderConfig

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama3"
OLLAMA_DEFAULT_URL = "http://localhost:11434"


class OllamaProvider(BaseLLMProvider):

    def __init__(self):
        config = ProviderConfig(
            name="ollama",
            models=[DEFAULT_MODEL, "mistral", "phi3"],
            priority=2,  # Lowest priority — used only as last resort
        )
        super().__init__(config)
        self._base_url = os.getenv("OLLAMA_BASE_URL", OLLAMA_DEFAULT_URL)

    def is_available(self) -> bool:
        try:
            r = requests.get(f"{self._base_url}/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False

    def generate(self, prompt: str, model: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 2048) -> LLMResponse:
        model = model or DEFAULT_MODEL

        def _inner():
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            r = requests.post(f"{self._base_url}/api/generate", json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            return LLMResponse(
                content=data.get("response", ""),
                provider=self.name,
                model=model,
                prompt_tokens=data.get("prompt_eval_count", 0),
                completion_tokens=data.get("eval_count", 0),
                success=True,
            )

        return self._timed_generate(_inner)
