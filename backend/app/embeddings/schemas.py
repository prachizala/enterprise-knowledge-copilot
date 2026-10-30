"""Pydantic schemas for embedding operations, status, and reindexing."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class EmbeddingTaskResponse(BaseModel):
    """Response returned upon initiating or completing document embedding generation."""

    document_id: str = Field(..., description="ID of document processed")
    status: str = Field(..., description="Resulting embedding status: completed, failed, processing")
    total_chunks: int = Field(..., description="Total number of chunks evaluated")
    embedded_chunks: int = Field(..., description="Number of chunks successfully embedded")
    model: str = Field(..., description="Embedding model identifier used")
    message: str = Field(..., description="Human-readable summary of the embedding operation")

    model_config = ConfigDict(from_attributes=True)


class DocumentEmbeddingStatusResponse(BaseModel):
    """Detailed embedding status and metadata for a specific document."""

    document_id: str = Field(..., description="Document identifier")
    embedding_status: str = Field(
        ...,
        description="Status: not_started, pending, processing, completed, failed",
    )
    total_chunks: int = Field(..., description="Total chunks belonging to document")
    embedded_chunks: int = Field(..., description="Number of chunks currently embedded")
    embedding_model: Optional[str] = Field(None, description="Model used for chunk embeddings")
    is_up_to_date: bool = Field(True, description="True if all chunks have fresh embeddings matching content hash")
    last_embedded_at: Optional[datetime] = Field(None, description="Timestamp of most recent embedding")

    model_config = ConfigDict(from_attributes=True)


class ReindexRequest(BaseModel):
    """Request payload for mass embedding reindexing."""

    force: bool = Field(
        default=False,
        description="If True, re-embed even if chunk content has not changed",
    )
    document_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of specific document IDs to reindex. If None, reindexes all.",
    )


class ReindexResponse(BaseModel):
    """Result summary of a reindexing run."""

    total_documents: int = Field(..., description="Total documents inspected")
    processed_documents: int = Field(..., description="Documents successfully processed")
    total_chunks_embedded: int = Field(..., description="Chunks newly embedded")
    skipped_chunks: int = Field(..., description="Chunks skipped due to unchanged content hash")
    failed_documents: int = Field(0, description="Documents that encountered errors")
    errors: List[str] = Field(default_factory=list, description="Sanitized list of error messages")
