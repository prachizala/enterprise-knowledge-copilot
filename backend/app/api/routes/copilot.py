from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.copilot.schemas import (
    CopilotChatRequest,
    CopilotMessageResponse,
    ConversationDetail,
    ConversationSummary,
    FeedbackRequest,
    FeedbackResponse,
)
from app.copilot.service import CopilotService
from app.core.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["Copilot"])


def get_copilot_service() -> CopilotService:
    return CopilotService()


@router.post("/chat", response_model=CopilotMessageResponse)
async def chat(
    request: CopilotChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
):
    """
    Send a message to Enterprise Copilot.
    Executes GraphRAG retrieval (vector + Neo4j multi-hop), builds anti-injection context,
    generates grounded response with numerical citations, scores groundedness, and records conversation.
    """
    try:
        return await service.chat(
            db=db,
            request=request,
            current_user=current_user,
        )
    except Exception as e:
        logger.error(f"Error processing copilot chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chat: {str(e)}",
        )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
):
    """List recent conversation sessions."""
    user_id = current_user.id if current_user else None
    return await service.list_conversations(db=db, user_id=user_id, limit=limit)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
):
    """Get full conversation detail including turn history and citations."""
    conversation = await service.get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
):
    """Delete a conversation session and all its messages."""
    deleted = await service.delete_conversation(db=db, conversation_id=conversation_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return {"deleted": True, "conversation_id": conversation_id}


@router.post("/messages/{message_id}/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    message_id: str,
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
    service: CopilotService = Depends(get_copilot_service),
):
    """Submit user rating and feedback on a copilot response."""
    user_id = current_user.id if current_user else None
    result = await service.add_feedback(
        db=db,
        message_id=message_id,
        feedback_data=feedback,
        user_id=user_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )
    return result
