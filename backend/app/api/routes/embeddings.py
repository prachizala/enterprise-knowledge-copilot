"""Global embedding operations and reindexing endpoints."""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.embeddings.schemas import ReindexRequest, ReindexResponse
from app.embeddings.service import EmbeddingService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/reindex",
    response_model=ReindexResponse,
    status_code=status.HTTP_200_OK,
    summary="Reindex Document Embeddings",
    description="Batch re-embed document chunks with staleness checking and optional force mode.",
)
async def reindex_embeddings(
    request: ReindexRequest = ReindexRequest(),
    db: AsyncSession = Depends(get_db),
) -> ReindexResponse:
    """Trigger embedding reindexing across all or selected documents."""
    logger.info("Triggering reindex (force=%s, doc_count=%s)", request.force, len(request.document_ids or []))
    return await EmbeddingService.reindex_all_embeddings(
        db=db,
        force=request.force,
        document_ids=request.document_ids,
    )
