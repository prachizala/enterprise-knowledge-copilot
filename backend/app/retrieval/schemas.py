"""Pydantic schemas for Advanced GraphRAG retrieval pipeline."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryAnalysis(BaseModel):
    """Structured understanding of user natural language query."""
    raw_query: str
    normalized_query: str
    query_category: str = Field(
        "factual_lookup",
        description="factual_lookup, entity_lookup, relationship_query, organizational_query, document_lookup, project_lookup, policy_lookup, technology_lookup, comparison_query, multi_hop_query, cross_document_query",
    )
    detected_entities: List[str] = Field(default_factory=list)
    extracted_filters: Dict[str, Any] = Field(default_factory=dict)
    is_multi_hop: bool = False
    requires_comparison: bool = False
    temporal_constraint: Optional[str] = None

    @property
    def category(self) -> str:
        return self.query_category

    @property
    def entities_mentioned(self) -> List[str]:
        return self.detected_entities

    @property
    def requires_graph(self) -> bool:
        return self.is_multi_hop or self.query_category in ["multi_hop_query", "relationship_query", "multi_hop"]


class LinkedEntity(BaseModel):
    """Query entity mention grounded to database Entity record."""
    entity_id: str
    canonical_name: str
    display_name: str
    entity_type: str
    mention_text: str
    confidence: float = 1.0
    match_type: str = "exact"  # exact, alias, normalized, vector_similarity
    is_ambiguous: bool = False
    candidate_alternatives: List[Dict[str, Any]] = Field(default_factory=list)


class VectorCandidate(BaseModel):
    """Document chunk candidate retrieved from pgvector search."""
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    similarity_score: float
    department: str = "General"
    content_hash: Optional[str] = None


class SparseCandidate(BaseModel):
    """Document chunk candidate retrieved from keyword / BM25 lexical search."""
    chunk_id: str
    document_id: str
    document_title: str
    chunk_index: int
    page_number: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    bm25_score: float
    matched_terms: List[str] = Field(default_factory=list)
    department: str = "General"
    content_hash: Optional[str] = None

    @property
    def similarity_score(self) -> float:
        return self.bm25_score


class GraphCandidate(BaseModel):
    """Entity and relationship candidate retrieved from Knowledge Graph."""
    entity_id: str
    canonical_name: str
    entity_type: str
    direct_relationships: List[Dict[str, Any]] = Field(default_factory=list)
    degree: int = 0
    relevance_score: float = 1.0
    associated_chunk_ids: List[str] = Field(default_factory=list)
    associated_document_ids: List[str] = Field(default_factory=list)


class GraphPath(BaseModel):
    """Multi-hop reasoning path through knowledge graph topology."""
    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    hops: int = 1
    formatted_path: str
    evidence_texts: List[str] = Field(default_factory=list)
    source_chunk_ids: List[str] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    confidence: float = 1.0


class FusedCandidate(BaseModel):
    """Merged candidate combining vector, graph, and path evidence."""
    chunk_id: str
    document_id: str
    document_title: str = "Document"
    document_name: Optional[str] = None
    chunk_index: int = 0
    page_number: Optional[int] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_title: Optional[str] = None
    content: str
    vector_score: float = 0.0
    sparse_score: float = 0.0
    graph_score: float = 0.0
    rrf_score: float = 0.0
    final_score: float = 0.0
    fused_score: float = 0.0
    origin: str = "hybrid"  # vector, sparse, graph, hybrid, tri-hybrid
    evidence_type: str = "document_chunk"
    connected_entities: List[str] = Field(default_factory=list)
    matched_keywords: List[str] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        if self.document_name and (not self.document_title or self.document_title == "Document"):
            self.document_title = self.document_name
        elif self.document_title and not self.document_name:
            self.document_name = self.document_title

        if self.page_start is not None and self.page_number is None:
            self.page_number = self.page_start
        elif self.page_number is not None and self.page_start is None:
            self.page_start = self.page_number

        if self.fused_score and not self.final_score:
            self.final_score = self.fused_score
        elif self.final_score and not self.fused_score:
            self.fused_score = self.final_score


class GroundedContext(BaseModel):
    """Structured grounded context payload passed to LLM generation."""
    query: str
    query_analysis: QueryAnalysis
    linked_entities: List[LinkedEntity]
    vector_candidates_count: int
    graph_candidates_count: int
    graph_paths: List[GraphPath]
    selected_evidence: List[FusedCandidate]
    formatted_context_str: str
    total_characters: int
    total_chunks: int
    latency_ms: Dict[str, float] = Field(default_factory=dict)

    @property
    def has_evidence(self) -> bool:
        return len(self.selected_evidence) > 0 or len(self.graph_paths) > 0

    @property
    def formatted_context(self) -> str:
        return self.formatted_context_str

    @property
    def candidates(self) -> List[FusedCandidate]:
        return self.selected_evidence


class RetrievalSearchRequest(BaseModel):
    """User query payload for retrieval search API."""
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(8, ge=1, le=50)
    min_similarity: float = Field(0.20, ge=0.0, le=1.0)
    department: Optional[str] = None
    document_id: Optional[str] = None
    depth: int = Field(2, ge=1, le=3)
    include_graph: bool = True
    vector_weight: float = Field(0.50, ge=0.0, le=1.0)
    graph_weight: float = Field(0.50, ge=0.0, le=1.0)
    rrf_k: int = Field(60, ge=1, le=100)


class RetrievalSearchResponse(BaseModel):
    """Public retrieval API response."""
    query_analysis: QueryAnalysis
    linked_entities: List[LinkedEntity]
    candidates: List[FusedCandidate]
    graph_paths: List[GraphPath]
    selected_evidence: List[FusedCandidate]
    total_candidates: int
    latencies: Dict[str, float]


class RetrievalDebugResponse(BaseModel):
    """Detailed internal retrieval trace for administrators and diagnostics."""
    request: RetrievalSearchRequest
    query_analysis: QueryAnalysis
    linked_entities: List[LinkedEntity]
    vector_candidates: List[VectorCandidate]
    graph_candidates: List[GraphCandidate]
    graph_paths: List[GraphPath]
    fused_candidates: List[FusedCandidate]
    selected_evidence: List[FusedCandidate]
    context_preview: str
    latencies: Dict[str, float]


# Legacy Vector Search Models for Backward Compatibility (Step 6 API)
class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(8, ge=1, le=50)
    similarity_threshold: float = Field(0.0, ge=0.0, le=1.0)
    department: Optional[str] = None
    document_id: Optional[str] = None
    file_type: Optional[str] = None


class VectorSearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    document_filename: str
    document_original_filename: str
    department: str
    owner: str
    file_type: str
    chunk_index: int
    content: str
    char_count: int
    token_count: int
    page_number: Optional[int] = None
    section_header: Optional[str] = None
    similarity_score: float
    distance: float
    model: str


class VectorSearchResponse(BaseModel):
    query: str
    total_results: int
    top_k: int
    results: List[VectorSearchResultItem]
    search_time_ms: float
    model: str
