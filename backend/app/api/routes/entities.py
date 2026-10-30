"""Entity API endpoints — canonical entity search and detail retrieval."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.extraction.entities.service import EntityExtractionService
from app.extraction.entities.schemas import EntityListResponse, EntityResponse
from app.extraction.entities.registry import ENTITY_TYPES_SORTED
from app.extraction.relationships.schemas import EntityRelationshipsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/search",
    response_model=EntityListResponse,
    summary="Search canonical entities",
    description="Search all canonical entities by name substring with optional type filter.",
)
async def search_entities(
    q: str = Query(..., min_length=1, description="Search query (substring match on canonical name)"),
    entity_type: Optional[str] = Query(None, description=f"Filter by entity type. Options: {', '.join(ENTITY_TYPES_SORTED)}"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=200, description="Results per page"),
    db: AsyncSession = Depends(get_db),
) -> EntityListResponse:
    """Search canonical entities by name with optional type filter."""
    entities, total = await EntityExtractionService.search_entities(
        db=db,
        q=q,
        entity_type=entity_type,
        page=page,
        page_size=page_size,
    )
    return EntityListResponse(
        total=total,
        page=page,
        page_size=page_size,
        entities=[EntityResponse(**e) for e in entities],
    )


@router.get(
    "/{entity_id}",
    response_model=EntityResponse,
    summary="Get canonical entity details",
    description="Retrieve full details for a canonical entity by its UUID.",
)
async def get_entity(
    entity_id: str,
    db: AsyncSession = Depends(get_db),
) -> EntityResponse:
    """Return canonical entity metadata by ID."""
    entity = await EntityExtractionService.get_entity_by_id(db=db, entity_id=entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found",
        )
    return EntityResponse(**entity)


@router.get(
    "/{entity_id}/relationships",
    response_model=EntityRelationshipsResponse,
    summary="Get Entity Relationships",
    description="Retrieve all incoming and outgoing typed relationships for a specific entity.",
)
async def get_entity_relationships(
    entity_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> EntityRelationshipsResponse:
    """Return incoming and outgoing relationships for this entity."""
    entity = await EntityExtractionService.get_entity_by_id(db=db, entity_id=entity_id)
    if entity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Entity '{entity_id}' not found",
        )
    from app.extraction.relationships.service import RelationshipExtractionService
    data = await RelationshipExtractionService.get_entity_relationships(
        db=db, entity_id=entity_id, page=page, page_size=page_size
    )
    return EntityRelationshipsResponse(**data)

