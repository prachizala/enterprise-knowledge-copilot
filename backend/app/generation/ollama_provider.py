"""Ollama LLM Provider for local, free, zero-cost private inference."""

import json
import logging
from typing import AsyncGenerator, List, Optional
import httpx

from app.core.config import settings
from app.generation.base import LLMProvider

logger = logging.getLogger(__name__)


class OllamaLLMProvider(LLMProvider):
    """Local Large Language Model generation provider using Ollama (Llama 3.2, Qwen 2.5, Mistral, etc.)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 90.0,
    ) -> None:
        self._base_url = (base_url or getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")).rstrip("/")
        self._model = model_name or getattr(settings, "OLLAMA_MODEL", "llama3.2")
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def base_url(self) -> str:
        return self._base_url

    async def generate(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs,
    ) -> str:
        """Call Ollama /api/chat non-streaming endpoint."""
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                return data.get("message", {}).get("content", "").strip()
        except httpx.ConnectError:
            logger.warning("Ollama service not running at %s. Returning fallback.", self._base_url)
            return (
                f"Ollama local service is not reachable at {self._base_url}. "
                f"Please ensure Ollama is running (`ollama serve`) and model '{self._model}' is pulled."
            )
        except Exception as e:
            logger.error("Ollama generation failed: %s", str(e))
            raise RuntimeError(f"Ollama generation failed: {str(e)}") from e

    async def stream_generate(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens chunk-by-chunk from Ollama."""
        url = f"{self._base_url}/api/chat"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk_data = json.loads(line)
                            token = chunk_data.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except Exception:
                            continue
        except httpx.ConnectError:
            yield (
                f"Ollama local service is not reachable at {self._base_url}. "
                f"Please run `ollama serve` and pull '{self._model}'."
            )
        except Exception as e:
            yield f"\n[Error streaming from Ollama: {str(e)}]"
