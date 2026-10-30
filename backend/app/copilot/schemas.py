from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class CopilotChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000, description="User question or query")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID if continuing session")
    department: Optional[str] = Field(None, description="Optional department filter")
    document_ids: Optional[List[str]] = Field(None, description="Optional document filter")
    include_graph: bool = Field(True, description="Enable Neo4j graph traversal")
    max_depth: int = Field(2, ge=1, le=3, description="Graph multi-hop depth")
    stream: bool = Field(False, description="Request streaming response")


class CitationItem(BaseModel):
    citation_index: int
    document_id: str
    document_name: str
    chunk_id: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_title: Optional[str] = None
    excerpt: str
    relevance_score: float = 1.0
    evidence_type: str = "document_chunk"


class CopilotMessageResponse(BaseModel):
    id: str
    conversation_id: str
    sender: str
    content: str
    grounding_score: Optional[float] = None
    query_category: Optional[str] = None
    citations: List[CitationItem] = []
    retrieval_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int = 0
    created_at: datetime
    updated_at: datetime


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[CopilotMessageResponse] = []


class FeedbackRequest(BaseModel):
    rating: str = Field(..., description="'helpful', 'not_helpful', 'incorrect', 'missing_info'")
    feedback_text: Optional[str] = Field(None, max_length=2000, description="Optional feedback notes")


class FeedbackResponse(BaseModel):
    id: str
    message_id: str
    rating: str
    feedback_text: Optional[str] = None
    created_at: datetime
