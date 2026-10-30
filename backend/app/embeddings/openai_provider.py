"""OpenAI embedding provider implementation with robust retries, batching, and error handling."""

import asyncio
import logging
from typing import List, Optional

import httpx

from app.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """Generates dense vector embeddings using OpenAI's API."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "text-embedding-3-small",
        dimensions: int = 1536,
        timeout: int = 60,
        max_retries: int = 3,
        batch_size: int = 32,
        base_url: str = "https://api.openai.com/v1",
    ) -> None:
        if not api_key or not api_key.strip():
            raise EmbeddingConfigurationError("OpenAI API key must be provided and non-empty.")
        self._api_key = api_key.strip()
        self._model_name = model_name
        self._dimensions = dimensions
        self._timeout = timeout
        self._max_retries = max_retries
        self._batch_size = max(1, batch_size)
        self._base_url = base_url.rstrip("/")

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def _post_with_retry(self, client: httpx.AsyncClient, payload: dict) -> dict:
        """Execute POST request with exponential backoff for rate limits and server errors."""
        url = f"{self._base_url}/embeddings"
        last_exception: Optional[Exception] = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=float(self._timeout),
                )
                if response.status_code == 200:
                    return response.json()

                # Rate limiting or temporary server issues
                if response.status_code in (429, 500, 502, 503, 504):
                    logger.warning(
                        "OpenAI embeddings transient status %d on attempt %d/%d",
                        response.status_code,
                        attempt,
                        self._max_retries,
                    )
                    if attempt < self._max_retries:
                        backoff = 2 ** attempt
                        await asyncio.sleep(backoff)
                        continue

                # Non-retryable error
                error_msg = f"OpenAI API error ({response.status_code}): {response.text[:200]}"
                if response.status_code in (401, 403):
                    raise EmbeddingConfigurationError(f"Authentication failed: {error_msg}")
                raise EmbeddingProviderUnavailableError(error_msg)

            except httpx.TimeoutException as e:
                logger.warning("OpenAI API request timed out on attempt %d/%d", attempt, self._max_retries)
                last_exception = e
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)
            except httpx.RequestError as e:
                logger.warning("OpenAI network error on attempt %d/%d: %s", attempt, self._max_retries, str(e))
                last_exception = e
                if attempt < self._max_retries:
                    await asyncio.sleep(2 ** attempt)

        raise EmbeddingProviderUnavailableError(
            f"OpenAI service unavailable after {self._max_retries} attempts: {str(last_exception)}"
        )

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts using OpenAI embedding endpoint."""
        if not texts:
            return []

        all_embeddings: List[List[float]] = []

        async with httpx.AsyncClient() as client:
            # Process in batches
            for i in range(0, len(texts), self._batch_size):
                batch = texts[i : i + self._batch_size]
                # Clean and sanitize batch strings
                cleaned_batch = [t if t and t.strip() else " " for t in batch]

                payload = {
                    "model": self._model_name,
                    "input": cleaned_batch,
                }
                # Request dimensions explicitly if supported
                if "text-embedding-3" in self._model_name:
                    payload["dimensions"] = self._dimensions

                data = await self._post_with_retry(client, payload)

                items = data.get("data", [])
                # Ensure ordered by index
                items.sort(key=lambda x: x.get("index", 0))

                for item in items:
                    vec = item.get("embedding", [])
                    if len(vec) != self._dimensions:
                        raise EmbeddingDimensionMismatchError(
                            f"Expected {self._dimensions} dimensions but got {len(vec)}"
                        )
                    all_embeddings.append(vec)

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed a single search query."""
        results = await self.embed_texts([query])
        if not results:
            raise EmbeddingError("Failed to obtain embedding for query")
        return results[0]
