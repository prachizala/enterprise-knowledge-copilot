"""Abstract base classes and custom exceptions for embedding providers."""

from abc import ABC, abstractmethod
from typing import List


class EmbeddingError(Exception):
    """Base exception for all embedding-related errors."""
    pass


class EmbeddingConfigurationError(EmbeddingError):
    """Raised when an embedding provider has invalid or missing configuration."""
    pass


class EmbeddingProviderUnavailableError(EmbeddingError):
    """Raised when an external embedding provider is unreachable or times out."""
    pass


class EmbeddingDimensionMismatchError(EmbeddingError):
    """Raised when the vector returned does not match expected dimensions."""
    pass


class EmbeddingProvider(ABC):
    """Abstract interface defining the contract for embedding providers."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the identifier of the embedding model."""
        pass

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the vector dimensionality produced by this model."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of text strings into normalized dense float vectors.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of float vectors, each of length self.dimensions.
        """
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Embed a single query string into a normalized dense float vector.

        Args:
            query: User's search query string.

        Returns:
            Single float vector of length self.dimensions.
        """
        pass
