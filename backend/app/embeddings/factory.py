"""Factory for instantiating configured embedding providers with fallback safety."""

import logging
from typing import Optional

from app.core.config import settings
from app.embeddings.base import EmbeddingProvider
from app.embeddings.mock_provider import MockEmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider

logger = logging.getLogger(__name__)

_active_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Return the active singleton EmbeddingProvider based on application configuration."""
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    provider_name = (settings.EMBEDDING_PROVIDER or "mock").lower()

    if provider_name == "openai":
        api_key = (settings.EMBEDDING_API_KEY or settings.OPENAI_API_KEY or "").strip()
        if not api_key:
            logger.warning(
                "EMBEDDING_PROVIDER is 'openai' but neither EMBEDDING_API_KEY nor OPENAI_API_KEY is configured. "
                "Falling back to MockEmbeddingProvider for offline operation."
            )
            _active_provider = MockEmbeddingProvider(
                model_name=settings.EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIMENSIONS,
            )
        else:
            logger.info("Initializing OpenAIEmbeddingProvider with model: %s", settings.EMBEDDING_MODEL)
            _active_provider = OpenAIEmbeddingProvider(
                api_key=api_key,
                model_name=settings.EMBEDDING_MODEL,
                dimensions=settings.EMBEDDING_DIMENSIONS,
                timeout=settings.EMBEDDING_TIMEOUT_SECONDS,
                max_retries=settings.EMBEDDING_MAX_RETRIES,
                batch_size=settings.EMBEDDING_BATCH_SIZE,
            )
    else:
        logger.info("Initializing MockEmbeddingProvider with model: %s", settings.EMBEDDING_MODEL)
        _active_provider = MockEmbeddingProvider(
            model_name=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )

    return _active_provider


def set_embedding_provider(provider: Optional[EmbeddingProvider]) -> None:
    """Explicitly override the embedding provider (useful for testing)."""
    global _active_provider
    _active_provider = provider
