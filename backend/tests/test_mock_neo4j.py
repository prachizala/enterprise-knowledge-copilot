"""Test suite verifying In-Memory Mock Neo4j Fallback functionality."""

import pytest
from app.core.config import settings
from app.graph.client import Neo4jClient
from app.graph.repository import GraphRepository


@pytest.mark.asyncio
async def test_mock_neo4j_forced_via_setting():
    """Verify that setting MOCK_NEO4J=True enables in-memory mock mode without contacting network."""
    orig_mock = settings.MOCK_NEO4J
    try:
        settings.MOCK_NEO4J = True
        client = Neo4jClient()
        connected = await client.connect()
        assert connected is True
        assert client.is_mock is True

        health = await client.check_health()
        assert health["status"] == "healthy"
        assert health["mock_mode"] is True
        assert health["node_count"] > 0
        assert health["relationship_count"] > 0
    finally:
        settings.MOCK_NEO4J = orig_mock


@pytest.mark.asyncio
async def test_mock_neo4j_automatic_fallback_when_unreachable():
    """Verify that when Neo4j container is offline, client gracefully activates mock mode instead of raising."""
    orig_mock = settings.MOCK_NEO4J
    orig_uri = settings.NEO4J_URI
    try:
        settings.MOCK_NEO4J = False
        settings.NEO4J_URI = "bolt://localhost:9999"  # invalid unreachable port
        client = Neo4jClient()
        connected = await client.connect()
        assert connected is True
        assert client.is_mock is True

        records = await client.execute_query("MATCH (n) RETURN count(n) AS node_count")
        assert len(records) == 1
        assert "node_count" in records[0]
    finally:
        settings.MOCK_NEO4J = orig_mock
        settings.NEO4J_URI = orig_uri


@pytest.mark.asyncio
async def test_graph_repository_with_mock_neo4j():
    """Verify GraphRepository returns structured GraphNode and Subgraph models under mock mode."""
    orig_mock = settings.MOCK_NEO4J
    try:
        settings.MOCK_NEO4J = True
        client = Neo4jClient()
        await client.connect()
        repo = GraphRepository(client=client)

        # Search entities
        nodes = await repo.search_entities("copilot")
        assert len(nodes) > 0
        assert any("copilot" in n.canonical_name.lower() for n in nodes)

        # Get entity detail
        first_id = nodes[0].id
        detail = await repo.get_entity_detail(first_id)
        assert detail is not None
        assert detail.entity.id == first_id

        # Subgraph query
        subgraph = await repo.get_subgraph(first_id)
        assert subgraph is not None
        assert len(subgraph.nodes) > 0
    finally:
        settings.MOCK_NEO4J = orig_mock
