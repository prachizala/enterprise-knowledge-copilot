"""Health check API endpoints."""

import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", summary="General Health Check")
@router.get("/", include_in_schema=False)
async def health_check() -> Dict[str, Any]:
    """Return general service operational status."""
    return {
        "status": "healthy",
        "service": "enterprise-knowledge-copilot",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "version": settings.VERSION,
        "services": {
            "database_postgres": {"status": "configured_standby"},
            "graph_neo4j": {"status": "configured_standby"},
            "llm_service": {"status": "configured_standby"},
        },
    }


@router.get("/database", summary="Database Connectivity Health Check")
@router.get("/database/", include_in_schema=False)
async def database_health_check(
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Test actual database connectivity by executing a verification query."""
    try:
        result = await db.execute(text("SELECT 1"))
        value = result.scalar()
        if value != 1:
            raise ValueError(f"Unexpected query result: {value}")
        return {
            "status": "healthy",
            "database": "connected",
        }
    except Exception as exc:
        logger.error(f"Database health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(exc),
            },
        )


@router.get("/neo4j", summary="Neo4j Knowledge Graph Health Check")
@router.get("/neo4j/", include_in_schema=False)
async def neo4j_health_check() -> Dict[str, Any]:
    """Test actual Neo4j connectivity and return operational state without leaking credentials."""
    from app.graph.health import check_neo4j_health
    result = await check_neo4j_health()
    if result.get("status") == "healthy":
        return {
            "status": "healthy",
            "database": "neo4j",
            "connected": True,
            "node_count": result.get("node_count", 0),
            "relationship_count": result.get("relationship_count", 0),
        }
    return {
        "status": "unhealthy",
        "database": "neo4j",
        "connected": False,
    }
