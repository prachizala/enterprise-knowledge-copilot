"""Models for retrieval and answer evaluation benchmarks."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def generate_uuid_str() -> str:
    """Generate string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class EvaluationRun(Base):
    """A benchmark run evaluating GraphRAG retrieval and answer groundedness."""

    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Enterprise Benchmark Run",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending",
        doc="'pending', 'running', 'completed', 'failed'",
    )
    total_queries: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    avg_recall: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    avg_precision: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    avg_groundedness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    avg_citation_coverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    hallucination_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    avg_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )

    results: Mapped[list["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="run",
        cascade="all, delete-orphan",
    )


class EvaluationResult(Base):
    """Detailed query-level evaluation result within an evaluation run."""

    __tablename__ = "evaluation_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
    )
    run_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expected_answer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    actual_answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    groundedness_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    citation_coverage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )

    run: Mapped["EvaluationRun"] = relationship(
        "EvaluationRun",
        back_populates="results",
    )
