"""Conversation, message, citation, and user feedback models."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base


def generate_uuid_str() -> str:
    """Generate string UUID4."""
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Conversation(Base):
    """Multi-turn conversation session."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
        doc="Conversation UUID",
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Owner user ID",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="New Enterprise Copilot Chat",
        doc="Conversation topic title",
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

    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at",
    )


class ConversationMessage(Base):
    """A single turn/message within a Copilot conversation."""

    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="'user' or 'copilot'",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Message markdown text content",
    )
    grounding_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Answer grounding confidence score (0.0 - 1.0)",
    )
    query_category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Detected query classification category",
    )
    retrieval_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        doc="Retrieval diagnostics, latencies, matched entities, graph paths",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation",
        back_populates="messages",
    )
    citations: Mapped[List["MessageCitation"]] = relationship(
        "MessageCitation",
        back_populates="message",
        cascade="all, delete-orphan",
        order_by="MessageCitation.citation_index",
    )
    feedback: Mapped[List["MessageFeedback"]] = relationship(
        "MessageFeedback",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class MessageCitation(Base):
    """Verified source citation attached to a Copilot answer."""

    __tablename__ = "message_citations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    citation_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Citation marker index [1], [2], etc.",
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    document_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    chunk_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    page_start: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    page_end: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    section_title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    excerpt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Verbatim grounded evidence excerpt",
    )
    relevance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=1.0,
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="document_chunk",
        doc="'document_chunk' or 'graph_relationship'",
    )

    message: Mapped["ConversationMessage"] = relationship(
        "ConversationMessage",
        back_populates="citations",
    )


class MessageFeedback(Base):
    """User evaluation feedback on a Copilot answer."""

    __tablename__ = "message_feedback"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid_str,
        index=True,
    )
    message_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversation_messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )
    rating: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="'helpful', 'not_helpful', 'incorrect', 'missing_info'",
    )
    feedback_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional user textual notes/explanation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=get_utc_now,
    )

    message: Mapped["ConversationMessage"] = relationship(
        "ConversationMessage",
        back_populates="feedback",
    )
