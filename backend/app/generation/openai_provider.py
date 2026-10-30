"""OpenAI LLM provider using httpx client."""

import logging
from typing import Optional
import httpx

from app.core.config import settings
from app.generation.base import LLMProvider

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """Generates answers via OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: float = 45.0,
    ) -> None:
        self._api_key = api_key or settings.LLM_API_KEY or settings.OPENAI_API_KEY
        self._model = model_name or settings.LLM_MODEL or "gpt-4o-mini"
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        prompt: str,
        system_instruction: str,
        max_tokens: int = 1500,
        temperature: float = 0.1,
    ) -> str:
        if not self._api_key:
            raise ValueError("OpenAI API key is not configured for LLM answer generation.")

        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            res = await client.post(url, headers=headers, json=payload)
            if res.status_code != 200:
                logger.error("OpenAI LLM generation failed: HTTP %s - %s", res.status_code, res.text)
                raise RuntimeError(f"OpenAI LLM generation failed with HTTP {res.status_code}")

            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                return "I couldn't find sufficient evidence in the available enterprise knowledge base to answer this reliably."
            return choices[0]["message"]["content"].strip()
