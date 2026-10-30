"""Pydantic schemas for entity extraction results."""

import re
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.extraction.entities.registry import ENTITY_TYPES, normalize_entity_type


class ExtractedEntity(BaseModel):
    """A single entity extracted from a chunk of text."""

    text: str = Field(..., min_length=1, description="Surface form as it appears in the source text")
    type: str = Field(..., description="Entity type, must be a recognized canonical type")
    normalized_name: str = Field(..., min_length=1, description="Canonically normalized entity name for deduplication")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence in [0.0, 1.0]")
    start_char: Optional[int] = Field(None, ge=0, description="Start offset in chunk text (0-based)")
    end_char: Optional[int] = Field(None, ge=0, description="End offset in chunk text (exclusive)")

    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, v: str) -> str:
        """Normalize type to uppercase; map unknown → OTHER."""
        return normalize_entity_type(str(v))

    @field_validator("text", "normalized_name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def end_after_start(self) -> "ExtractedEntity":
        if self.start_char is not None and self.end_char is not None:
            if self.end_char <= self.start_char:
                raise ValueError("end_char must be greater than start_char")
        return self


class EntityExtractionResult(BaseModel):
    """Aggregated result from a single chunk extraction call."""

    chunk_id: str
    content_hash: str
    provider: str
    model: str
    entities: List[ExtractedEntity] = Field(default_factory=list)
    error: Optional[str] = None


class EntityExtractionStats(BaseModel):
    """Statistics returned from document-level entity extraction."""

    document_id: str
    total_chunks: int = 0
    processed_chunks: int = 0
    skipped_chunks: int = 0
    failed_chunks: int = 0
    entities_found: int = 0
    unique_entities: int = 0


# ── API-level response schemas ──────────────────────────────────────────────

class EntityResponse(BaseModel):
    """Serialized canonical entity returned by the API."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    entity_type: str
    canonical_name: str
    display_name: str
    description: Optional[str] = None
    mention_count: int = 0
    document_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class EntityListResponse(BaseModel):
    """Paginated list of canonical entities."""
    total: int
    page: int
    page_size: int
    entities: List[EntityResponse]


class ChunkEntityResponse(BaseModel):
    """A single entity mention in a specific chunk."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    chunk_id: str
    entity_id: str
    document_id: str
    mention_text: str
    confidence: float
    entity_type: str = ""          # populated from joined Entity
    canonical_name: str = ""       # populated from joined Entity
    section_header: Optional[str] = None
    page_number: Optional[int] = None


class DocumentEntityStatusResponse(BaseModel):
    """Entity extraction status for a single document."""
    document_id: str
    entity_extraction_status: str
    entity_mention_count: int
    unique_entity_count: int
    total_chunks: int


class EntityExtractionTaskResponse(BaseModel):
    """Response after triggering entity extraction for a document."""
    document_id: str
    task: str = "entity_extraction"
    status: str
    message: str
