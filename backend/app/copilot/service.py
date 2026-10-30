from __future__ import annotations

import logging
from typing import AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.copilot.schemas import (
    CitationItem,
    CopilotChatRequest,
    CopilotMessageResponse,
    ConversationDetail,
    ConversationSummary,
    FeedbackRequest,
    FeedbackResponse,
)
from app.generation.service import LLMGenerationService
from app.models.conversation import (
    Conversation,
    ConversationMessage,
    MessageCitation,
    MessageFeedback,
)
from app.models.user import User
from app.retrieval.schemas import RetrievalSearchRequest
from app.retrieval.service import GraphRAGRetrievalService

logger = logging.getLogger(__name__)


class CopilotService:
    def __init__(
        self,
        retrieval_service: Optional[GraphRAGRetrievalService] = None,
        generation_service: Optional[LLMGenerationService] = None,
    ) -> None:
        self.retrieval_service = retrieval_service or GraphRAGRetrievalService()
        self.generation_service = generation_service or LLMGenerationService()

    async def chat(
        self,
        db: AsyncSession,
        request: CopilotChatRequest,
        current_user: Optional[User] = None,
    ) -> CopilotMessageResponse:
        # 1. Resolve or create conversation
        conversation: Optional[Conversation] = None
        if request.conversation_id:
            res = await db.execute(
                select(Conversation)
                .where(Conversation.id == request.conversation_id)
                .options(selectinload(Conversation.messages))
            )
            conversation = res.scalars().first()

        if not conversation:
            # Generate descriptive title from first query
            title = request.message[:60].strip()
            if len(request.message) > 60:
                title += "..."
            conversation = Conversation(
                id=str(uuid4()),
                user_id=current_user.id if current_user else None,
                title=title,
            )
            db.add(conversation)
            await db.flush()

        # 2. Gather conversation history for multi-turn context
        history_res = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conversation.id)
            .order_by(desc(ConversationMessage.created_at))
            .limit(6)
        )
        prev_msgs = list(reversed(history_res.scalars().all()))
        chat_history = [{"role": msg.sender, "content": msg.content} for msg in prev_msgs]

        # 3. Save incoming user message
        user_msg = ConversationMessage(
            id=str(uuid4()),
            conversation_id=conversation.id,
            sender="user",
            content=request.message,
        )
        db.add(user_msg)
        await db.flush()

        # 4. Perform GraphRAG Retrieval
        grounded_context = await self.retrieval_service.retrieve(
            db=db,
            query=request.message,
            user=current_user,
            top_k=5,
            department=request.department,
            document_id=request.document_ids[0] if request.document_ids else None,
            depth=request.max_depth,
            include_graph=request.include_graph,
        )

        # 5. Generate Grounded Answer with LLM
        gen_resp = await self.generation_service.generate_answer(
            query=request.message,
            grounded_context=grounded_context,
            chat_history=chat_history,
        )

        # 6. Save Copilot message
        copilot_msg_id = str(uuid4())
        retrieval_metadata = {
            "query_analysis": grounded_context.query_analysis.model_dump(),
            "fused_count": len(grounded_context.candidates),
            "graph_paths_count": len(grounded_context.graph_paths),
            "latencies_ms": grounded_context.latency_ms,
            "provider": gen_resp.provider,
            "model": gen_resp.model,
            "tokens_used": gen_resp.tokens_used,
            "latency_ms": gen_resp.latency_ms,
        }

        copilot_msg = ConversationMessage(
            id=copilot_msg_id,
            conversation_id=conversation.id,
            sender="copilot",
            content=gen_resp.answer,
            grounding_score=gen_resp.grounding_score,
            query_category=grounded_context.query_analysis.category,
            retrieval_metadata=retrieval_metadata,
        )
        db.add(copilot_msg)
        await db.flush()

        # 7. Save message citations
        citation_items: List[CitationItem] = []
        for c in gen_resp.citations:
            citation_model = MessageCitation(
                id=str(uuid4()),
                message_id=copilot_msg_id,
                citation_index=c.citation_index,
                document_id=c.document_id,
                document_name=c.document_name,
                chunk_id=c.chunk_id,
                page_start=c.page_start,
                page_end=c.page_end,
                section_title=c.section_title,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
                evidence_type=c.evidence_type,
            )
            db.add(citation_model)
            citation_items.append(
                CitationItem(
                    citation_index=c.citation_index,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    chunk_id=c.chunk_id,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section_title=c.section_title,
                    excerpt=c.excerpt,
                    relevance_score=c.relevance_score,
                    evidence_type=c.evidence_type,
                )
            )

        conversation.updated_at = copilot_msg.created_at
        await db.commit()
        await db.refresh(copilot_msg)

        return CopilotMessageResponse(
            id=copilot_msg.id,
            conversation_id=conversation.id,
            sender="copilot",
            content=copilot_msg.content,
            grounding_score=copilot_msg.grounding_score,
            query_category=copilot_msg.query_category,
            citations=citation_items,
            retrieval_metadata=retrieval_metadata,
            created_at=copilot_msg.created_at,
        )

    async def list_conversations(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ConversationSummary]:
        query = (
            select(
                Conversation.id,
                Conversation.title,
                Conversation.created_at,
                Conversation.updated_at,
                func.count(ConversationMessage.id).label("message_count"),
            )
            .outerjoin(ConversationMessage, Conversation.id == ConversationMessage.conversation_id)
            .group_by(Conversation.id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        if user_id:
            query = query.where(Conversation.user_id == user_id)

        res = await db.execute(query)
        rows = res.all()
        return [
            ConversationSummary(
                id=r.id,
                title=r.title,
                created_at=r.created_at,
                updated_at=r.updated_at,
                message_count=r.message_count,
            )
            for r in rows
        ]

    async def get_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> Optional[ConversationDetail]:
        res = await db.execute(
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(
                selectinload(Conversation.messages).selectinload(ConversationMessage.citations)
            )
        )
        conversation = res.scalars().first()
        if not conversation:
            return None

        messages = []
        for msg in conversation.messages:
            citations = [
                CitationItem(
                    citation_index=c.citation_index,
                    document_id=c.document_id,
                    document_name=c.document_name,
                    chunk_id=c.chunk_id,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    section_title=c.section_title,
                    excerpt=c.excerpt,
                    relevance_score=c.relevance_score,
                    evidence_type=c.evidence_type,
                )
                for c in (msg.citations or [])
            ]
            messages.append(
                CopilotMessageResponse(
                    id=msg.id,
                    conversation_id=msg.conversation_id,
                    sender=msg.sender,
                    content=msg.content,
                    grounding_score=msg.grounding_score,
                    query_category=msg.query_category,
                    citations=citations,
                    retrieval_metadata=msg.retrieval_metadata,
                    created_at=msg.created_at,
                )
            )

        return ConversationDetail(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages,
        )

    async def delete_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
    ) -> bool:
        res = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conversation = res.scalars().first()
        if not conversation:
            return False

        await db.delete(conversation)
        await db.commit()
        return True

    async def add_feedback(
        self,
        db: AsyncSession,
        message_id: str,
        feedback_data: FeedbackRequest,
        user_id: Optional[str] = None,
    ) -> Optional[FeedbackResponse]:
        res = await db.execute(
            select(ConversationMessage).where(ConversationMessage.id == message_id)
        )
        message = res.scalars().first()
        if not message:
            return None

        feedback = MessageFeedback(
            id=str(uuid4()),
            message_id=message_id,
            user_id=user_id,
            rating=feedback_data.rating,
            feedback_text=feedback_data.feedback_text,
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        return FeedbackResponse(
            id=feedback.id,
            message_id=feedback.message_id,
            rating=feedback.rating,
            feedback_text=feedback.feedback_text,
            created_at=feedback.created_at,
        )
