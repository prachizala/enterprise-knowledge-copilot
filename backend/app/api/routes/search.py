"""Semantic vector search endpoints."""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.retrieval.schemas import VectorSearchRequest, VectorSearchResponse
from app.retrieval.vector_search import VectorSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/vector",
    response_model=VectorSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Semantic Vector Search",
    description="Embeds natural-language query and searches chunk embeddings using cosine similarity with document provenance.",
)
async def semantic_vector_search(
    request: VectorSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> VectorSearchResponse:
    """Execute vector similarity search across indexed document chunks."""
    logger.info("Executing vector search for query: '%s' (top_k=%d)", request.query, request.top_k)
    return await VectorSearchService.search(db=db, request=request)
