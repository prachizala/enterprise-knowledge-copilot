"""Tests for root and health check endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch
from app.core.config import settings


@pytest.mark.asyncio
async def test_read_root(client: AsyncClient):
    """Test GET / returns 200 with required greeting and status."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Enterprise Knowledge Copilot API"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Test GET /api/health returns general health metadata."""
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "enterprise-knowledge-copilot"
    assert data["app_name"] == settings.APP_NAME
    assert data["version"] == settings.VERSION


@pytest.mark.asyncio
async def test_database_health_check_success(client: AsyncClient):
    """Test GET /api/health/database returns 200 when DB query succeeds."""
    response = await client.get("/api/health/database")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_database_health_check_failure(client: AsyncClient):
    """Test GET /api/health/database returns 503 when DB connectivity is broken."""
    with patch("sqlalchemy.ext.asyncio.AsyncSession.execute", side_effect=Exception("Database unreachable")):
        response = await client.get("/api/health/database")
        assert response.status_code == 503
        data = response.json()
        assert "detail" in data
        assert data["detail"]["status"] == "unhealthy"
        assert data["detail"]["database"] == "disconnected"


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    """Test CORS preflight response headers."""
    response = await client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
