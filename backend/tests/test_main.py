"""Tests for Enterprise Knowledge Copilot root and health endpoints."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.core.config import settings

client = TestClient(app)


def test_read_root() -> None:
    """Test GET / returns required message and status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Enterprise Knowledge Copilot API"
    assert data["status"] == "running"


def test_api_health() -> None:
    """Test GET /api/health returns health status and service metadata."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert "services" in data
    assert "database_postgres" in data["services"]
    assert "graph_neo4j" in data["services"]
    assert "llm_service" in data["services"]
    assert data["services"]["database_postgres"]["status"] == "configured_standby"
    assert data["services"]["graph_neo4j"]["status"] == "configured_standby"


def test_cors_headers() -> None:
    """Test that CORS headers allow communication with Next.js frontend."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
