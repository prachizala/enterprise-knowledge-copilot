"""OpenAI LLM-based entity extraction provider.

Uses OpenAI chat completions with JSON mode to extract structured entities.
Requires OPENAI_API_KEY to be set. Falls back gracefully if unavailable.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from app.extraction.entities.base import (
    EntityExtractionError,
    EntityExtractionProvider,
    EntityExtractionTimeoutError,
)
from app.extraction.entities.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class LLMEntityExtractionProvider(EntityExtractionProvider):
    """Entity extraction via OpenAI chat completions with JSON mode.

    Security: Never logs full text, chunk content, or complete API responses.
    """

    def __init__(self, api_key: str, model: str, timeout_seconds: int, max_retries: int) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract_entities(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Call OpenAI with retry logic and return raw entity dicts."""
        try:
            from openai import AsyncOpenAI, APIError, APITimeoutError
        except ImportError as exc:
            raise EntityExtractionError("openai package not installed") from exc

        client = AsyncOpenAI(api_key=self._api_key, timeout=float(self._timeout))
        context = metadata.get("section_header", "")
        user_message = build_user_prompt(text, context=context)

        last_exc: Exception = Exception("No attempts made")
        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_message},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                )
                raw = response.choices[0].message.content or "[]"
                # Model may wrap the array in a JSON object
                parsed = json.loads(raw)
                if isinstance(parsed, dict):
                    # Find the first list value
                    for v in parsed.values():
                        if isinstance(v, list):
                            parsed = v
                            break
                    else:
                        parsed = []
                if not isinstance(parsed, list):
                    parsed = []

                logger.debug(
                    "LLM extraction returned %d entities (attempt %d/%d)",
                    len(parsed),
                    attempt,
                    self._max_retries,
                )
                return parsed

            except APITimeoutError as exc:
                last_exc = exc
                logger.warning("LLM entity extraction timeout (attempt %d/%d)", attempt, self._max_retries)
                if attempt == self._max_retries:
                    raise EntityExtractionTimeoutError(
                        f"LLM extraction timed out after {self._max_retries} attempts"
                    ) from exc
                await asyncio.sleep(2 ** attempt)

            except APIError as exc:
                last_exc = exc
                logger.warning("LLM entity extraction API error (attempt %d/%d): %s", attempt, self._max_retries, type(exc).__name__)
                if attempt == self._max_retries:
                    raise EntityExtractionError(f"LLM extraction failed: {type(exc).__name__}") from exc
                await asyncio.sleep(2 ** attempt)

            except (json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                logger.warning("LLM extraction response parse error (attempt %d/%d)", attempt, self._max_retries)
                if attempt == self._max_retries:
                    raise EntityExtractionError("Failed to parse LLM extraction response") from exc
                await asyncio.sleep(1)

        raise EntityExtractionError("LLM extraction failed after all retries") from last_exc
