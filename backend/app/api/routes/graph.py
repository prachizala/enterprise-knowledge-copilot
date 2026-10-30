"""Knowledge Graph API routes: synchronization, entity exploration, neighbors, and subgraphs."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.graph.repository import graph_repository
from app.graph.schemas import (
    GraphEntityDetailResponse,
    GraphNeighborsResponse,
    GraphNode,
    GraphSyncRequest,
    GraphSyncResponse,
    SubgraphResponse,
)
from app.graph.sync_service import graph_sync_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/sync",
    response_model=GraphSyncResponse,
    summary="Synchronize PostgreSQL to Neo4j",
    description="Synchronize entities, relationships, chunks, and documents into the Neo4j Knowledge Graph.",
)
async def sync_knowledge_graph(
    payload: Optional[GraphSyncRequest] = None,
    document_id: Optional[str] = Query(None, description="Optional document UUID for scoped sync"),
    force: bool = Query(False, description="Force re-synchronization of existing records"),
    db: AsyncSession = Depends(get_db),
) -> GraphSyncResponse:
    """Execute graph synchronization pipeline."""
    target_doc_id = (payload.document_id if payload else None) or document_id
    force_sync = (payload.force if payload else False) or force

    res = await graph_sync_service.sync(db=db, document_id=target_doc_id, force=force_sync)
    if res.errors > 0 and (res.entities_synced == 0 and res.relationships_synced == 0):
        # Report connection or sync failure
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=res.message,
        )
    return res


@router.get(
    "/entities/search",
    response_model=List[GraphNode],
    summary="Search Graph Entities",
    description="Find graph entity nodes by substring match on canonical or display name.",
)
async def search_graph_entities(
    q: str = Query(..., min_length=1, description="Entity search query"),
    limit: int = Query(20, ge=1, le=100, description="Max entities to return"),
) -> List[GraphNode]:
    """Search entity nodes in Neo4j."""
    try:
        return await graph_repository.search_entities(query=q, limit=limit)
    except ConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j Knowledge Graph service is currently unavailable",
        )


@router.get(
    "/entities/{entity_id}",
    response_model=GraphEntityDetailResponse,
    summary="Get Graph Entity Detail",
    description="Retrieve entity information, incoming/outgoing relationships, and document provenance.",
)
async def get_graph_entity(
    entity_id: str,
) -> GraphEntityDetailResponse:
    """Get single entity details with connected edges and source documents."""
    try:
        detail = await graph_repository.get_entity_detail(entity_id=entity_id)
        if detail is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entity '{entity_id}' not found in Knowledge Graph",
            )
        return detail
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j Knowledge Graph service is currently unavailable",
        )


@router.get(
    "/entities/{entity_id}/neighbors",
    response_model=GraphNeighborsResponse,
    summary="Get Entity Neighbors",
    description="Retrieve connected neighbor nodes and edges up to depth N.",
)
async def get_graph_neighbors(
    entity_id: str,
    depth: int = Query(1, ge=1, le=3, description="Traversal depth (1 to 3 hops)"),
    relationship_type: Optional[str] = Query(None, description="Optional relationship filter"),
    limit: int = Query(50, ge=1, le=100, description="Max neighbor nodes to return"),
) -> GraphNeighborsResponse:
    """Retrieve N-hop neighborhood for an entity."""
    try:
        return await graph_repository.get_entity_neighbors(
            entity_id=entity_id,
            depth=depth,
            relationship_type=relationship_type,
            limit=limit,
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j Knowledge Graph service is currently unavailable",
        )


@router.get(
    "/subgraph/{entity_id}",
    response_model=SubgraphResponse,
    summary="Get Entity Subgraph",
    description="Extract a bounded subgraph around an entity for interactive visualization and GraphRAG.",
)
async def get_entity_subgraph(
    entity_id: str,
    depth: int = Query(2, ge=1, le=3, description="Maximum traversal depth"),
    max_nodes: int = Query(100, ge=1, le=250, description="Safety limit on maximum nodes returned"),
    max_relationships: int = Query(200, ge=1, le=500, description="Safety limit on maximum relationships"),
) -> SubgraphResponse:
    """Extract a bounded subgraph centered at entity_id."""
    try:
        return await graph_repository.get_subgraph(
            entity_id=entity_id,
            depth=depth,
            max_nodes=max_nodes,
            max_relationships=max_relationships,
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j Knowledge Graph service is currently unavailable",
        )


@router.get(
    "/document/{document_id}",
    response_model=SubgraphResponse,
    summary="Get Document Subgraph",
    description="Retrieve all entities and relationships originating from or referenced in a specific document.",
)
async def get_document_subgraph(
    document_id: str,
    max_nodes: int = Query(100, ge=1, le=250),
    max_relationships: int = Query(200, ge=1, le=500),
) -> SubgraphResponse:
    """Retrieve subgraph for a single document."""
    try:
        return await graph_repository.get_document_subgraph(
            document_id=document_id,
            max_nodes=max_nodes,
            max_relationships=max_relationships,
        )
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Neo4j Knowledge Graph service is currently unavailable",
        )
