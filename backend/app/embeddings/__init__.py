"""Embeddings generation and vector operations package."""

from app.embeddings.base import (
    EmbeddingConfigurationError,
    EmbeddingDimensionMismatchError,
    EmbeddingError,
    EmbeddingProvider,
    EmbeddingProviderUnavailableError,
)
from app.embeddings.factory import get_embedding_provider, set_embedding_provider
from app.embeddings.mock_provider import MockEmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.schemas import (
    DocumentEmbeddingStatusResponse,
    EmbeddingTaskResponse,
    ReindexRequest,
    ReindexResponse,
)
from app.embeddings.service import EmbeddingService

__all__ = [
    "EmbeddingError",
    "EmbeddingConfigurationError",
    "EmbeddingProviderUnavailableError",
    "EmbeddingDimensionMismatchError",
    "EmbeddingProvider",
    "MockEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "get_embedding_provider",
    "set_embedding_provider",
    "EmbeddingService",
    "EmbeddingTaskResponse",
    "DocumentEmbeddingStatusResponse",
    "ReindexRequest",
    "ReindexResponse",
]
