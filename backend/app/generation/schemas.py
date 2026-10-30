"""Pydantic schemas for LLM answer generation and verified citations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    """Verified, grounded citation attached to an answer claim."""
    citation_id: int = Field(1, description="Citation marker index [1], [2], etc.")
    document_id: str
    document_name: str
    chunk_id: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_title: Optional[str] = None
    excerpt: str
    relevance_score: float = 1.0
    evidence_type: str = "document_chunk"  # document_chunk, graph_relationship

    def __init__(self, **data: Any):
        if "citation_index" in data and "citation_id" not in data:
            data["citation_id"] = data["citation_index"]
        super().__init__(**data)

    @property
    def citation_index(self) -> int:
        return self.citation_id


class GenerationResponse(BaseModel):
    """Full grounded answer generation response."""
    query: str = ""
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    grounding_score: float = Field(1.0, ge=0.0, le=1.0)
    confidence_status: str = Field("grounded", description="'grounded', 'cautious', 'insufficient_evidence'")
    unsupported_claims: List[str] = Field(default_factory=list)
    has_conflicts: bool = False
    conflict_notes: Optional[str] = None
    graph_insights: Optional[str] = None
    entities_matched: List[str] = Field(default_factory=list)
    tokens_used: int = 0
    generation_time_ms: float = 0.0
    latency_ms: float = 0.0
    provider: str = "mock"
    model: str = "gpt-4o-mini"
    has_insufficient_evidence: bool = False
