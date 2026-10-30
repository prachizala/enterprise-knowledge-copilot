"""Asynchronous document processing job models for observability and retry tracking."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


def generate_uuid_str() -> str:
    """Generate string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class ProcessingJob(Base):
    """Tracks background ingestion and synchronization jobs for documents."""

    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Job UUID",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Associated document UUID",
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="full_pipeline",
        doc="'full_pipeline', 'extract', 'chunk', 'embed', 'entities', 'relationships', 'graph_sync'",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
        doc="'pending', 'running', 'completed', 'failed', 'retrying'",
    )
    current_step: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        doc="Current pipeline step name",
    )
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        doc="Completion percentage 0-100",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed error trace if failed",
    )
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Step metrics: chunks_count, entities_count, relationships_count, duration_ms",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
        onupdate=get_utc_now,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
