"""Abstract base class and exception hierarchy for relationship extraction providers."""

import abc
from typing import Any, Dict, List


class RelationshipExtractionError(Exception):
    """Raised when relationship extraction provider encounters an unrecoverable failure."""


class RelationshipExtractionTimeoutError(RelationshipExtractionError):
    """Raised when relationship extraction call exceeds the configured timeout."""


class RelationshipExtractionProvider(abc.ABC):
    """Abstract interface for all relationship extraction providers.

    Relationship extractors must be stateless and thread/coroutine safe.
    They receive:
      1. chunk_text: Raw text content of the DocumentChunk
      2. entities: List of entities identified in this chunk (with alias_id, text, type, canonical_name)
      3. metadata: Contextual metadata (chunk_id, document_id, section_header, etc.)

    And return:
      List of raw relationship dictionaries:
        {
          "source_entity": str (e.g. alias_id "E1" or entity text),
          "relationship_type": str,
          "target_entity": str (e.g. alias_id "E2" or entity text),
          "confidence": float,
          "evidence_text": str | None,
          "source_start_char": int | None,
          "source_end_char": int | None,
          "target_start_char": int | None,
          "target_end_char": int | None,
        }

    Security: Implementations MUST NOT log full chunk text or sensitive responses.
    """

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Short identifier for this provider, e.g. 'openai', 'mock'."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Name of the model being utilized, e.g. 'gpt-4o-mini', 'mock-v1'."""

    @abc.abstractmethod
    async def extract_relationships(
        self,
        chunk_text: str,
        entities: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Extract relationships between the supplied entities grounded in chunk_text.

        Args:
            chunk_text: Source text passage of the chunk.
            entities: Pre-identified entities available in this chunk.
            metadata: Context metadata (chunk_id, document_id, etc.).

        Returns:
            List of raw relationship dictionaries.

        Raises:
            RelationshipExtractionError: On provider failure.
            RelationshipExtractionTimeoutError: On request timeout.
        """
