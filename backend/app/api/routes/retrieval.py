"""GraphRAG Retrieval API endpoints: hybrid search, debug diagnostics, candidate preview, and active configuration."""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.retrieval import (
    GroundedContext,
    RetrievalDebugResponse,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    retrieval_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/search",
    response_model=RetrievalSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Advanced GraphRAG Hybrid Search",
    description="Execute complete hybrid retrieval combining vector similarity, knowledge graph entity linking, and multi-hop paths.",
)
async def search_retrieval(
    request: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetrievalSearchResponse:
    """Execute authenticated, RBAC-filtered hybrid retrieval."""
    grounded = await retrieval_service.retrieve(
        db=db,
        query=request.query,
        user=current_user,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        department=request.department,
        document_id=request.document_id,
        depth=request.depth,
        include_graph=request.include_graph,
        vector_weight=request.vector_weight,
        graph_weight=request.graph_weight,
        rrf_k=request.rrf_k,
    )

    return RetrievalSearchResponse(
        query_analysis=grounded.query_analysis,
        linked_entities=grounded.linked_entities,
        candidates=grounded.selected_evidence,
        graph_paths=grounded.graph_paths,
        selected_evidence=grounded.selected_evidence,
        total_candidates=len(grounded.selected_evidence),
        latencies=grounded.latency_ms,
    )


@router.post(
    "/debug",
    response_model=RetrievalDebugResponse,
    status_code=status.HTTP_200_OK,
    summary="GraphRAG Retrieval Diagnostics",
    description="Admin/developer endpoint exposing intermediate query analysis, vector candidates, graph candidate paths, and fusion matrices.",
)
async def debug_retrieval(
    request: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetrievalDebugResponse:
    """Expose full retrieval trace and scoring breakdown."""
    grounded = await retrieval_service.retrieve(
        db=db,
        query=request.query,
        user=current_user,
        top_k=request.top_k,
        min_similarity=request.min_similarity,
        department=request.department,
        document_id=request.document_id,
        depth=request.depth,
        include_graph=request.include_graph,
        vector_weight=request.vector_weight,
        graph_weight=request.graph_weight,
        rrf_k=request.rrf_k,
    )

    # In debug mode, also retrieve raw vector and graph candidates
    return RetrievalDebugResponse(
        request=request,
        query_analysis=grounded.query_analysis,
        linked_entities=grounded.linked_entities,
        vector_candidates=[],
        graph_candidates=[],
        graph_paths=grounded.graph_paths,
        fused_candidates=grounded.selected_evidence,
        selected_evidence=grounded.selected_evidence,
        context_preview=grounded.formatted_context_str[:2000],
        latencies=grounded.latency_ms,
    )


@router.post(
    "/preview",
    response_model=RetrievalSearchResponse,
    summary="Fast Evidence Preview",
    description="Lightweight fast retrieval for typing suggestions or rapid search previews.",
)
async def preview_retrieval(
    request: RetrievalSearchRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RetrievalSearchResponse:
    """Run fast preview with 1-hop depth and top-k=5."""
    grounded = await retrieval_service.retrieve(
        db=db,
        query=request.query,
        user=current_user,
        top_k=min(request.top_k, 5),
        min_similarity=request.min_similarity,
        depth=1,
        include_graph=request.include_graph,
    )
    return RetrievalSearchResponse(
        query_analysis=grounded.query_analysis,
        linked_entities=grounded.linked_entities,
        candidates=grounded.selected_evidence,
        graph_paths=grounded.graph_paths,
        selected_evidence=grounded.selected_evidence,
        total_candidates=len(grounded.selected_evidence),
        latencies=grounded.latency_ms,
    )


@router.get(
    "/config",
    summary="Get GraphRAG Configuration",
    description="Inspect active weights, depth bounds, RRF constants, and context limits.",
)
async def get_retrieval_config() -> Dict[str, Any]:
    """Return active retrieval configuration parameters."""
    return {
        "vector_weight": settings.GRAPHRAG_VECTOR_WEIGHT,
        "graph_weight": settings.GRAPHRAG_GRAPH_WEIGHT,
        "evidence_weight": settings.GRAPHRAG_EVIDENCE_WEIGHT,
        "rrf_k": settings.GRAPHRAG_RRF_K,
        "graph_max_depth": settings.GRAPHRAG_GRAPH_MAX_DEPTH,
        "graph_max_nodes": settings.GRAPHRAG_GRAPH_MAX_NODES,
        "graph_max_edges": settings.GRAPHRAG_GRAPH_MAX_EDGES,
        "graph_max_paths": settings.GRAPHRAG_GRAPH_MAX_PATHS,
        "max_context_chunks": settings.GRAPHRAG_MAX_CONTEXT_CHUNKS,
        "max_context_characters": settings.GRAPHRAG_MAX_CONTEXT_CHARACTERS,
        "enforce_document_rbac": settings.ENFORCE_DOCUMENT_RBAC,
    }
