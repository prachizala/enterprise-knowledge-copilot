"""Main FastAPI application entrypoint for Enterprise Knowledge Copilot."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import async_engine
from app.schemas.health import RootResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup hooks: auto-create database tables if not existing
    try:
        from app.core.database import Base
        import app.models  # noqa: F401
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        pass

    # Startup hooks: attempt non-blocking Neo4j connection initialization
    try:
        from app.graph.client import get_neo4j_client
        client = get_neo4j_client()
        await client.connect()
    except Exception:
        pass
    yield
    # Shutdown hooks: cleanly dispose of Neo4j driver and PostgreSQL connection pools
    try:
        from app.graph.client import get_neo4j_client
        client = get_neo4j_client()
        await client.close()
    except Exception:
        pass
    await async_engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Enterprise Knowledge Copilot - Knowledge Graph RAG for Enterprise Data",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.CORS_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(
    "/",
    response_model=RootResponse,
    summary="Root Status",
    description="Returns the primary status of the Enterprise Knowledge Copilot API",
)
def read_root() -> Dict[str, str]:
    """Return initial root status of the API."""
    return {
        "message": "Enterprise Knowledge Copilot API",
        "status": "running",
    }


# Include Central API Router under /api prefix
app.include_router(api_router, prefix=settings.API_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
