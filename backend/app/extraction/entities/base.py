"""Abstract base class and exceptions for entity extraction providers."""

import abc
from typing import Any, Dict, List


class EntityExtractionError(Exception):
    """Raised when an entity extraction provider fails unrecoverably."""


class EntityExtractionTimeoutError(EntityExtractionError):
    """Raised when a provider call exceeds the configured timeout."""


class EntityExtractionProvider(abc.ABC):
    """Abstract interface for all entity extraction providers.

    Implementations must be stateless enough to be used concurrently.
    The `extract_entities` method receives chunk text and chunk metadata
    and must return a list of raw entity dictionaries that conform to the
    `ExtractedEntity` schema fields:

        {
            "text": str,
            "type": str,
            "normalized_name": str,
            "confidence": float,
            "start_char": int | None,
            "end_char": int | None,
        }

    Implementations MUST NOT log the full chunk text — only summary stats.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Short human-readable name for this provider, e.g. 'openai', 'mock'."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Name of the model being used, e.g. 'gpt-4o-mini', 'mock-v1'."""

    @abc.abstractmethod
    async def extract_entities(
        self,
        text: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract entities from *text* and return raw entity dicts.

        Args:
            text: Chunk text content to analyze.
            metadata: Auxiliary metadata (chunk_id, document_id, section_header, etc.)
                      that the provider may include in its prompt for context.

        Returns:
            List of raw entity dicts. Each must include at minimum 'text', 'type',
            'normalized_name', and 'confidence'. Partial/low-confidence entities
            should be returned with their confidence value, not silently dropped.

        Raises:
            EntityExtractionError: on unrecoverable failure.
            EntityExtractionTimeoutError: when the provider times out.
        """
