"""Relationship API routes: search and detail endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.extraction.relationships.schemas import (
    RelationshipListResponse,
    RelationshipResponse,
)
from app.extraction.relationships.service import RelationshipExtractionService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/search",
    response_model=RelationshipListResponse,
    summary="Search Entity Relationships",
    description="Search relationships across entity names, relationship types, and evidence text excerpts.",
)
async def search_relationships(
    q: str = Query(..., min_length=1, description="Query string matching entity names, relationship type, or evidence"),
    relationship_type: Optional[str] = Query(None, description="Optional relationship type filter"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> RelationshipListResponse:
    """Search relationships by text query and optional filters."""
    results, total = await RelationshipExtractionService.search_relationships(
        db=db,
        q=q,
        relationship_type=relationship_type,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )
    return RelationshipListResponse(
        total=total,
        page=page,
        page_size=page_size,
        relationships=results,
    )


@router.get(
    "/{relationship_id}",
    response_model=RelationshipResponse,
    summary="Get Relationship Detail",
    description="Retrieve full provenance, endpoints, evidence, and scores for a specific relationship.",
)
async def get_relationship(
    relationship_id: str,
    db: AsyncSession = Depends(get_db),
) -> RelationshipResponse:
    """Get single relationship by ID."""
    rel = await RelationshipExtractionService.get_relationship_by_id(
        db=db, relationship_id=relationship_id
    )
    if rel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship '{relationship_id}' not found",
        )
    return rel
