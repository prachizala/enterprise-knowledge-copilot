"""SQLAlchemy 2.x models for Entity and ChunkEntity (Step 7 — Entity Extraction)."""

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.document import generate_uuid_str, get_utc_now

if TYPE_CHECKING:
    from app.models.relationship import EntityRelationship


class Entity(Base):
    """Represents a canonical named entity deduplicated across all documents.

    Unique constraint on (entity_type, canonical_name) ensures that the same
    real-world concept maps to a single row regardless of surface form variation.
    """

    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique UUID identifier for the canonical entity",
    )
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Normalized entity type, e.g. PERSON, ORGANIZATION, TECHNOLOGY",
    )
    canonical_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        index=True,
        doc="Normalized canonical form of the entity name used for deduplication",
    )
    display_name: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Human-readable display name, preserved from first occurrence",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional descriptive context about the entity",
    )
    mention_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Cumulative number of times this entity has been mentioned",
    )
    document_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of distinct documents referencing this entity",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp when entity was first discovered",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last entity update",
    )

    # Relationship to chunk mentions
    chunk_mentions: Mapped[list["ChunkEntity"]] = relationship(
        "ChunkEntity",
        back_populates="entity",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    # Relationships to entity relationships (Step 8)
    outgoing_relationships: Mapped[list["EntityRelationship"]] = relationship(
        "EntityRelationship",
        primaryjoin="Entity.id == EntityRelationship.source_entity_id",
        back_populates="source_entity",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    incoming_relationships: Mapped[list["EntityRelationship"]] = relationship(
        "EntityRelationship",
        primaryjoin="Entity.id == EntityRelationship.target_entity_id",
        back_populates="target_entity",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    __table_args__ = (
        UniqueConstraint("entity_type", "canonical_name", name="uq_entity_type_canonical"),
        Index("idx_entity_type", "entity_type"),
        Index("idx_entity_canonical", "canonical_name"),
        Index("idx_entity_type_canonical", "entity_type", "canonical_name"),
    )


class ChunkEntity(Base):
    """Represents a single entity mention within a specific document chunk.

    Multiple rows can reference the same canonical Entity (many-to-one).
    Idempotency is enforced by content_hash + provider + model to prevent
    re-processing the same chunk with the same extraction configuration.
    """

    __tablename__ = "chunk_entities"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique UUID for this chunk-entity mention",
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to document_chunks.id",
    )
    entity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to entities.id",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Denormalized document FK for efficient document-level queries",
    )
    mention_text: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
        doc="Exact surface form text of the entity as it appeared in the chunk",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        doc="Extraction confidence score in range [0.0, 1.0]",
    )
    start_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Start character offset within chunk content (0-based)",
    )
    end_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="End character offset within chunk content (exclusive)",
    )
    extra_metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON-serialized extraction metadata (provider output, context)",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA-256 hash of the source chunk content at extraction time",
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Extraction provider name: llm, mock, spacy, etc.",
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Specific model used for extraction, e.g. gpt-4o-mini",
    )
    section_header: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Denormalized section heading from source chunk for provenance",
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Denormalized page number from source chunk for provenance",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp when mention was recorded",
    )

    # Relationships
    entity: Mapped["Entity"] = relationship(
        "Entity",
        back_populates="chunk_mentions",
    )

    __table_args__ = (
        Index("idx_chunk_entity_chunk", "chunk_id"),
        Index("idx_chunk_entity_entity", "entity_id"),
        Index("idx_chunk_entity_document", "document_id"),
        Index("idx_chunk_entity_hash_provider", "content_hash", "provider", "model"),
    )
