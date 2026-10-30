"""Central API router combining all subsystem route modules."""

from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.documents import router as documents_router
from app.api.routes.search import router as search_router
from app.api.routes.embeddings import router as embeddings_router
from app.api.routes.entities import router as entities_router
from app.api.routes.relationships import router as relationships_router
from app.api.routes.graph import router as graph_router
from app.api.routes.auth import router as auth_router
from app.api.routes.retrieval import router as retrieval_router
from app.api.routes.copilot import router as copilot_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.analytics import router as analytics_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Authentication & Access Control"])
api_router.include_router(health_router, prefix="/health", tags=["Health"])
api_router.include_router(copilot_router, prefix="/copilot", tags=["Copilot"])
api_router.include_router(documents_router, prefix="/documents", tags=["Documents"])
api_router.include_router(retrieval_router, prefix="/retrieval", tags=["GraphRAG Retrieval"])
api_router.include_router(search_router, prefix="/search", tags=["Vector Search"])
api_router.include_router(embeddings_router, prefix="/embeddings", tags=["Embeddings"])
api_router.include_router(entities_router, prefix="/entities", tags=["Entities"])
api_router.include_router(relationships_router, prefix="/relationships", tags=["Relationships"])
api_router.include_router(graph_router, prefix="/graph", tags=["Knowledge Graph"])
api_router.include_router(jobs_router, prefix="/jobs", tags=["Ingestion Jobs"])
api_router.include_router(evaluation_router, prefix="/evaluation", tags=["Evaluation & Benchmarks"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics & Telemetry"])

__all__ = ["api_router"]
