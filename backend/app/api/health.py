"""Health check API endpoints."""

from fastapi import APIRouter
from app.core.config import settings
from app.schemas.health import HealthResponse, ServiceStatus

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return health status of the API and its configured subsystem placeholders."""
    return HealthResponse(
        status="healthy",
        app_name=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        services={
            "database_postgres": ServiceStatus(
                name="PostgreSQL Database",
                status="configured_standby",
                configured=bool(settings.DATABASE_URL),
                details=f"Host: {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}, DB: {settings.POSTGRES_DB} (No active connection - Step 1)",
            ),
            "graph_neo4j": ServiceStatus(
                name="Neo4j Knowledge Graph",
                status="configured_standby",
                configured=bool(settings.NEO4J_URI),
                details=f"URI: {settings.NEO4J_URI} (No active connection - Step 1)",
            ),
            "llm_service": ServiceStatus(
                name="LLM Provider",
                status="configured_standby",
                configured=bool(settings.LLM_MODEL),
                details=f"Provider: {settings.LLM_PROVIDER}, Model: {settings.LLM_MODEL} (No active connection - Step 1)",
            ),
        },
    )
