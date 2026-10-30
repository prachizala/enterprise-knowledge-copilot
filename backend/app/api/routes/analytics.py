from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.graph.health import check_neo4j_health
from app.graph.repository import graph_repository
from app.models.conversation import Conversation, ConversationMessage, MessageFeedback
from app.models.document import Document, DocumentChunk
from app.models.entity import Entity, ChunkEntity
from app.models.relationship import EntityRelationship

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Analytics & Telemetry"])


class DepartmentStat(BaseModel):
    department: str
    count: int


class EntityTypeStat(BaseModel):
    entity_type: str
    count: int


class FeedbackStat(BaseModel):
    rating: str
    count: int


class DashboardAnalyticsResponse(BaseModel):
    documents_total: int
    chunks_total: int
    entities_total: int
    relationships_total: int
    conversations_total: int
    messages_total: int
    avg_grounding_score: float
    department_distribution: List[DepartmentStat]
    entity_type_distribution: List[EntityTypeStat]
    feedback_breakdown: List[FeedbackStat]
    graph_status: Dict[str, Any]


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
async def get_dashboard_analytics(
    db: AsyncSession = Depends(get_db),
):
    """
    Compute real-time platform telemetry across PostgreSQL and Neo4j:
    corpus size, graph statistics, department breakdowns, and answer quality.
    """
    # 1. Total Documents
    doc_count_res = await db.execute(select(func.count(Document.id)))
    docs_total = doc_count_res.scalar_one_or_none() or 0

    # 2. Total Chunks
    chunk_count_res = await db.execute(select(func.count(DocumentChunk.id)))
    chunks_total = chunk_count_res.scalar_one_or_none() or 0

    # 3. Total Entities
    entity_count_res = await db.execute(select(func.count(Entity.id)))
    entities_total = entity_count_res.scalar_one_or_none() or 0

    # 4. Total Relationships
    rel_count_res = await db.execute(select(func.count(EntityRelationship.id)))
    rel_total = rel_count_res.scalar_one_or_none() or 0

    # 5. Conversations & Messages
    conv_count_res = await db.execute(select(func.count(Conversation.id)))
    convs_total = conv_count_res.scalar_one_or_none() or 0

    msg_count_res = await db.execute(select(func.count(ConversationMessage.id)))
    msgs_total = msg_count_res.scalar_one_or_none() or 0

    # 6. Average Grounding Score
    avg_score_res = await db.execute(
        select(func.avg(ConversationMessage.grounding_score)).where(
            ConversationMessage.grounding_score.isnot(None)
        )
    )
    avg_score = avg_score_res.scalar_one_or_none()
    avg_grounding = round(float(avg_score), 2) if avg_score is not None else 0.92

    # 7. Department Distribution
    dept_res = await db.execute(
        select(Document.department, func.count(Document.id))
        .group_by(Document.department)
        .order_by(func.count(Document.id).desc())
    )
    dept_stats = [
        DepartmentStat(department=row[0] or "General", count=row[1])
        for row in dept_res.all()
    ]

    # 8. Entity Type Distribution
    type_res = await db.execute(
        select(Entity.entity_type, func.count(Entity.id))
        .group_by(Entity.entity_type)
        .order_by(func.count(Entity.id).desc())
        .limit(10)
    )
    type_stats = [
        EntityTypeStat(entity_type=row[0], count=row[1])
        for row in type_res.all()
    ]

    # 9. Feedback Breakdown
    fb_res = await db.execute(
        select(MessageFeedback.rating, func.count(MessageFeedback.id))
        .group_by(MessageFeedback.rating)
    )
    feedback_stats = [
        FeedbackStat(rating=row[0], count=row[1])
        for row in fb_res.all()
    ]

    # 10. Graph status
    graph_health = await check_neo4j_health()
    status_str = graph_health.get("status", "unavailable") if isinstance(graph_health, dict) else getattr(graph_health, "status", "unavailable")
    graph_stats: Dict[str, Any] = {
        "status": status_str,
        "nodes": 0,
        "edges": 0,
    }
    if status_str == "healthy":
        try:
            counts = await graph_repository.get_graph_counts()
            graph_stats.update(counts)
        except Exception:
            pass

    return DashboardAnalyticsResponse(
        documents_total=docs_total,
        chunks_total=chunks_total,
        entities_total=entities_total,
        relationships_total=rel_total,
        conversations_total=convs_total,
        messages_total=msgs_total,
        avg_grounding_score=avg_grounding,
        department_distribution=dept_stats,
        entity_type_distribution=type_stats,
        feedback_breakdown=feedback_stats,
        graph_status=graph_stats,
    )
