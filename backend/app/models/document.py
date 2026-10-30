"""SQLAlchemy 2.x Models for Document metadata and Extracted Text Content."""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.relationship import EntityRelationship


def generate_uuid_str() -> str:
    """Generate string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Document(Base):
    """Represents an enterprise document metadata record in PostgreSQL."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique UUID document identifier",
    )
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Normalized internal filename",
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Original uploaded filename from user",
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Document MIME/extension type: pdf, docx, txt, csv",
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Size in bytes",
    )
    department: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
        index=True,
        doc="Associated business unit or department",
    )
    owner: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="System",
        doc="Document custodian or creator",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Summary or description of document contents",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        index=True,
        doc="Lifecycle state: uploaded, processing, processed, failed",
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0",
        doc="Document version identifier",
    )

    # Step 4 Storage & Extraction Fields
    storage_path: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        doc="Relative path in safe storage volume (data/uploads/<id>/...)",
    )
    mime_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Validated MIME type",
    )
    extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        doc="Extraction state: pending, processing, completed, failed",
    )
    extracted_text_length: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Length of extracted text in characters",
    )
    processing_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Sanitized processing or extraction error description",
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Timestamp when extraction processing completed",
    )

    # Phase 16 & 20: Access Control, Deduplication & Pipeline Fields
    visibility: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="organization",
        doc="Visibility scope: 'organization', 'department', or 'restricted'",
    )
    allowed_roles: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Comma-separated RBAC roles permitted to access when restricted (e.g. 'ADMIN,MANAGER')",
    )
    allowed_users: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Comma-separated user IDs permitted to access when restricted",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA-256 binary hash of the source file for idempotency/deduplication",
    )
    graph_sync_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="Neo4j Knowledge Graph sync status: 'pending', 'synced', 'failed'",
    )

    # Step 5 Chunking Fields
    total_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total number of discrete chunks generated for this document",
    )

    # Step 6 Embedding Fields
    embedding_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_started",
        index=True,
        doc="Embedding status: not_started, pending, processing, completed, failed",
    )
    embedded_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of chunks with embeddings generated",
    )
    embedding_model: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Model used for embeddings, e.g. text-embedding-3-small",
    )

    # Step 7 Entity Extraction Fields
    entity_extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_started",
        index=True,
        doc="Entity extraction state: not_started, processing, completed, partial, failed",
    )
    entity_mention_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total entity mentions extracted across all chunks",
    )
    unique_entity_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Number of distinct canonical entities identified in this document",
    )

    # Step 8 Relationship Extraction Fields
    relationship_extraction_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="not_started",
        index=True,
        doc="Relationship extraction state: not_started, processing, completed, partial, failed",
    )
    relationship_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total entity relationships extracted for this document",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        index=True,
        doc="Timestamp of registration",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last update",
    )

    # Relationship to extracted text content
    content: Mapped[Optional["DocumentContent"]] = relationship(
        "DocumentContent",
        back_populates="document",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Relationship to document chunks
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
        lazy="selectin",
    )

    # Relationship to chunk embeddings
    embeddings: Mapped[List["ChunkEmbedding"]] = relationship(
        "ChunkEmbedding",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Relationship to entity relationships (Step 8)
    relationships: Mapped[List["EntityRelationship"]] = relationship(
        "EntityRelationship",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_doc_dept_status", "department", "status"),
        Index("idx_doc_type_status", "file_type", "status"),
        Index("idx_doc_extract_status", "extraction_status"),
        Index("idx_doc_embed_status", "embedding_status"),
        Index("idx_doc_entity_status", "entity_extraction_status"),
        Index("idx_doc_rel_status", "relationship_extraction_status"),
    )


class DocumentContent(Base):
    """Represents extracted raw text and structural metadata for a document."""

    __tablename__ = "document_contents"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique content identifier",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
        doc="Foreign key to documents.id",
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Full extracted text content",
    )
    character_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total character count of extracted text",
    )
    word_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Total word count of extracted text",
    )
    page_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of pages (for PDF) or sections",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp when content was extracted",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last content update",
    )

    # Relationship back to Document
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="content",
    )


class DocumentChunk(Base):
    """Represents a discrete indexed text chunk derived from document content."""

    __tablename__ = "document_chunks"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique chunk UUID identifier",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to documents.id",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="0-based sequential order of chunk in the document",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Text passage content of the chunk",
    )
    char_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Character length of content",
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Estimated token count of content (~4 chars/token)",
    )
    page_number: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="1-based source page number where chunk originates (e.g. PDF)",
    )
    section_header: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Section or markdown heading context of chunk",
    )
    chunk_metadata: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="JSON serialized metadata payload (format, table flags, line numbers)",
    )
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="SHA-256 content hash for idempotency and cache invalidation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp of chunk creation",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last chunk update",
    )

    # Relationship back to parent document
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    # Relationship to embeddings
    embeddings: Mapped[List["ChunkEmbedding"]] = relationship(
        "ChunkEmbedding",
        back_populates="chunk",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # Relationship to entity relationships (Step 8)
    relationships: Mapped[List["EntityRelationship"]] = relationship(
        "EntityRelationship",
        back_populates="chunk",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_chunk_doc_index", "document_id", "chunk_index"),
        Index("idx_chunk_doc_page", "document_id", "page_number"),
        Index("idx_chunk_content_hash", "content_hash"),
    )


class ChunkEmbedding(Base):
    """Represents a dense semantic vector embedding for a document chunk."""

    __tablename__ = "chunk_embeddings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Unique embedding identifier",
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to document_chunks.id",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Foreign key to documents.id for fast document-level joins and deletions",
    )
    embedding: Mapped[Any] = mapped_column(
        Vector(1536),
        nullable=False,
        doc="Dense semantic vector embedding (1536 dimensions for text-embedding-3-small)",
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="text-embedding-3-small",
        index=True,
        doc="Model used to produce embedding",
    )
    dimensions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1536,
        doc="Vector dimension length",
    )
    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hash of chunk content when embedded, for freshness verification",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        nullable=False,
        doc="Timestamp of embedding generation",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=get_utc_now,
        onupdate=get_utc_now,
        nullable=False,
        doc="Timestamp of last update",
    )

    # Relationships
    chunk: Mapped["DocumentChunk"] = relationship(
        "DocumentChunk",
        back_populates="embeddings",
    )
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="embeddings",
    )

    __table_args__ = (
        UniqueConstraint("chunk_id", "model", name="uq_chunk_model_embedding"),
        Index(
            "idx_chunk_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("idx_embedding_doc_model", "document_id", "model"),
    )


# Compatibility aliases for legacy prototype references
DocumentModel = Document
DocumentChunkModel = DocumentChunk
ChunkEmbeddingModel = ChunkEmbedding


