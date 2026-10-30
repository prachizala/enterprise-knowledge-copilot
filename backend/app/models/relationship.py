"""SQLAlchemy 2.x models for Entity Relationships (Step 8 — Relationship Extraction)."""

from datetime import datetime, timezone
from typing import Any, Optional

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


class EntityRelationship(Base):
    """Represents a typed, grounded relationship between two canonical entities.

    Every relationship is grounded in a source document chunk and carries:
    - Typed connection from source entity to target entity
    - Confidence score (0.0 to 1.0)
    - Verifiable evidence text excerpt from the source chunk
    - Source and target character offsets within the chunk (if available)
    - Full provenance tracing back to chunk_id, document_id, provider, and model
    """

    __tablename__ = "entity_relationships"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique UUID identifier for this entity relationship",
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to source Entity (outgoing endpoint)",
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to target Entity (incoming endpoint)",
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Controlled vocabulary relationship type, e.g. WORKS_FOR, OWNS, USES",
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
        index=True,
        doc="Extraction confidence score in range [0.0, 1.0]",
    )
    evidence_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Grounded evidence excerpt from source chunk justifying the relationship",
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to the source document chunk providing the evidence",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Denormalized foreign key to documents.id for fast document-level queries",
    )
    source_start_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Start character offset of source entity mention in chunk text",
    )
    source_end_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="End character offset of source entity mention in chunk text",
    )
    target_start_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Start character offset of target entity mention in chunk text",
    )
    target_end_char: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="End character offset of target entity mention in chunk text",
    )
    extra_metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON-serialized extraction metadata (provider output, context flags)",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA-256 hash of the source chunk content at relationship extraction time",
    )
    provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Extraction provider name, e.g. openai, mock",
    )
    model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Extraction model name, e.g. gpt-4o-mini, mock-v1",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp when relationship was recorded",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last update",
    )

    # Relationships to endpoints
    source_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[source_entity_id],
        back_populates="outgoing_relationships",
    )
    target_entity: Mapped["Entity"] = relationship(
        "Entity",
        foreign_keys=[target_entity_id],
        back_populates="incoming_relationships",
    )

    # Relationships to chunk and document
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        foreign_keys=[chunk_id],
        back_populates="relationships",
    )
    document: Mapped["Document"] = relationship(
        "Document",
        foreign_keys=[document_id],
        back_populates="relationships",
    )

    __table_args__ = (
        UniqueConstraint(
            "source_entity_id",
            "target_entity_id",
            "relationship_type",
            "chunk_id",
            name="uq_entity_rel_source_target_type_chunk",
        ),
        Index("idx_rel_source_entity", "source_entity_id"),
        Index("idx_rel_target_entity", "target_entity_id"),
        Index("idx_rel_type", "relationship_type"),
        Index("idx_rel_chunk", "chunk_id"),
        Index("idx_rel_document", "document_id"),
        Index("idx_rel_confidence", "confidence"),
        Index("idx_rel_hash_provider", "content_hash", "provider", "model"),
    )
