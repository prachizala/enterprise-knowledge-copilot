"""Factory for instantiating the configured entity extraction provider.

Resolution order:
  1. If ENTITY_EXTRACTION_PROVIDER == "openai" and OPENAI_API_KEY is set → LLMEntityExtractionProvider
  2. Otherwise → MockEntityExtractionProvider (safe default, no API key required)

The singleton is cached per-process. Tests can override it via
set_entity_extraction_provider().
"""

import logging
from typing import Optional

from app.extraction.entities.base import EntityExtractionProvider

logger = logging.getLogger(__name__)

_provider_singleton: Optional[EntityExtractionProvider] = None


def get_entity_extraction_provider() -> EntityExtractionProvider:
    """Return the configured (or mock fallback) entity extraction provider."""
    global _provider_singleton
    if _provider_singleton is not None:
        return _provider_singleton

    from app.core.config import settings

    provider_name = (settings.ENTITY_EXTRACTION_PROVIDER or "").strip().lower()
    api_key = (settings.OPENAI_API_KEY or settings.EMBEDDING_API_KEY or "").strip()

    if provider_name == "openai" and api_key:
        try:
            from app.extraction.entities.llm_provider import LLMEntityExtractionProvider
            _provider_singleton = LLMEntityExtractionProvider(
                api_key=api_key,
                model=settings.ENTITY_EXTRACTION_MODEL,
                timeout_seconds=settings.ENTITY_EXTRACTION_TIMEOUT_SECONDS,
                max_retries=settings.ENTITY_EXTRACTION_MAX_RETRIES,
            )
            logger.info(
                "Entity extraction: using OpenAI provider with model %s",
                settings.ENTITY_EXTRACTION_MODEL,
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize LLM entity extraction provider (%s). Falling back to mock.",
                exc,
            )
            from app.extraction.entities.mock_provider import MockEntityExtractionProvider
            _provider_singleton = MockEntityExtractionProvider()
    else:
        from app.extraction.entities.mock_provider import MockEntityExtractionProvider
        _provider_singleton = MockEntityExtractionProvider()
        if provider_name:
            logger.warning(
                "Entity extraction provider '%s' configured but no API key found. Using mock.",
                provider_name,
            )
        else:
            logger.debug("No entity extraction provider configured. Using mock.")

    return _provider_singleton


def set_entity_extraction_provider(provider: Optional[EntityExtractionProvider]) -> None:
    """Override the provider singleton. Used in tests to inject mock provider.

    Pass None to reset the singleton so the factory re-evaluates settings.
    """
    global _provider_singleton
    _provider_singleton = provider
