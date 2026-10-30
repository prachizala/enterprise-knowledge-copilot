"""Pydantic schemas for relationship extraction, validation, and API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.extraction.relationships.normalization import normalize_relationship_type


class EntityInput(BaseModel):
    """An entity mention provided to the extraction provider for a chunk."""

    entity_id: str
    alias_id: str = Field(..., description="Short alias e.g. E1, E2")
    canonical_name: str
    display_name: str
    entity_type: str
    mention_text: str


class ExtractedRelationship(BaseModel):
    """A grounded, typed relationship between two entities in a chunk."""

    source_entity_text: str = Field(..., min_length=1, description="Source entity alias or mention text")
    source_entity_type: str = Field("", description="Source entity type")

    relationship_type: str = Field(..., min_length=1, description="Controlled relationship type")

    target_entity_text: str = Field(..., min_length=1, description="Target entity alias or mention text")
    target_entity_type: str = Field("", description="Target entity type")

    confidence: float = Field(..., ge=0.0, le=1.0, description="Extraction confidence score in [0.0, 1.0]")
    evidence_text: Optional[str] = Field(None, description="Verifiable evidence sentence or excerpt")

    source_start_char: Optional[int] = Field(None, ge=0)
    source_end_char: Optional[int] = Field(None, ge=0)

    target_start_char: Optional[int] = Field(None, ge=0)
    target_end_char: Optional[int] = Field(None, ge=0)

    @field_validator("relationship_type", mode="before")
    @classmethod
    def normalize_rel_type(cls, v: str) -> str:
        """Normalize relationship label to uppercase controlled vocabulary."""
        return normalize_relationship_type(str(v))

    @field_validator("source_entity_text", "target_entity_text", mode="before")
    @classmethod
    def strip_text(cls, v: str) -> str:
        s = str(v).strip()
        if not s:
            raise ValueError("Entity text cannot be empty")
        return s

    @model_validator(mode="after")
    def validate_no_self_reference(self) -> "ExtractedRelationship":
        """Prevent self-referential relationships."""
        if self.source_entity_text.strip().lower() == self.target_entity_text.strip().lower():
            raise ValueError("Self-referential relationships are not permitted")
        if self.source_start_char is not None and self.source_end_char is not None:
            if self.source_end_char <= self.source_start_char:
                raise ValueError("source_end_char must be greater than source_start_char")
        if self.target_start_char is not None and self.target_end_char is not None:
            if self.target_end_char <= self.target_start_char:
                raise ValueError("target_end_char must be greater than target_start_char")
        return self


class RelationshipExtractionResult(BaseModel):
    """Extraction output from a single chunk."""

    chunk_id: str
    content_hash: str
    provider: str
    model: str
    relationships: List[ExtractedRelationship] = Field(default_factory=list)
    unresolved_count: int = 0
    error: Optional[str] = None


class RelationshipExtractionStats(BaseModel):
    """Aggregated statistics returned from document-level relationship extraction."""

    document_id: str
    total_chunks: int = 0
    processed_chunks: int = 0
    relationships_found: int = 0
    relationships_created: int = 0
    unresolved: int = 0
    skipped: int = 0
    failed_chunks: int = 0


# ── API Response Schemas ─────────────────────────────────────────────────────

class EntitySummary(BaseModel):
    """Summary of an entity for relationship endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    canonical_name: str
    display_name: str
    entity_type: str


class RelationshipResponse(BaseModel):
    """Full detail of a persisted entity relationship with provenance."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_entity: EntitySummary
    target_entity: EntitySummary
    relationship_type: str
    confidence: float
    evidence_text: Optional[str] = None
    chunk_id: str
    document_id: str
    source_start_char: Optional[int] = None
    source_end_char: Optional[int] = None
    target_start_char: Optional[int] = None
    target_end_char: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RelationshipListResponse(BaseModel):
    """Paginated list of relationships."""

    total: int
    page: int
    page_size: int
    relationships: List[RelationshipResponse]


class EntityRelationshipsResponse(BaseModel):
    """All incoming and outgoing relationships for a specific entity."""

    entity_id: str
    total_outgoing: int
    total_incoming: int
    outgoing: List[RelationshipResponse]
    incoming: List[RelationshipResponse]


class DocumentRelationshipStatusResponse(BaseModel):
    """Relationship extraction status for a single document."""

    document_id: str
    relationship_extraction_status: str
    total_chunks: int
    processed_chunks: int
    relationships: int
    failed_chunks: int


class RelationshipExtractionTaskResponse(BaseModel):
    """Response returned when triggering relationship extraction."""

    document_id: str
    task: str = "relationship_extraction"
    status: str
    message: str
    stats: Optional[RelationshipExtractionStats] = None
