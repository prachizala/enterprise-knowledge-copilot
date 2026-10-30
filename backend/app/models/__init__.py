"""SQLAlchemy models package."""

from app.core.database import Base
from app.models.document import Document, DocumentContent, DocumentChunk, ChunkEmbedding
from app.models.entity import Entity, ChunkEntity
from app.models.relationship import EntityRelationship
from app.models.user import User, UserRole
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    MessageCitation,
    MessageFeedback,
)
from app.models.job import ProcessingJob
from app.models.evaluation import EvaluationRun, EvaluationResult

__all__ = [
    "Base",
    "Document",
    "DocumentContent",
    "DocumentChunk",
    "ChunkEmbedding",
    "Entity",
    "ChunkEntity",
    "EntityRelationship",
    "User",
    "UserRole",
    "Conversation",
    "ConversationMessage",
    "MessageCitation",
    "MessageFeedback",
    "ProcessingJob",
    "EvaluationRun",
    "EvaluationResult",
]
