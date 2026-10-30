"""Tests for Step 9 — Neo4j Knowledge Graph.

Comprehensive tests covering:
- Cypher relationship sanitization and whitelisting (injection prevention)
- Neo4jClient connection, queries, transactions, and health checks
- GraphRepository queries (search, get entity, entity detail, neighbors, bounded subgraphs)
- GraphSyncService (full database sync, document-scoped sync, idempotency)
- Graph API routes (/api/graph/sync, /api/graph/entities/search, /api/graph/entities/{id},
  /api/graph/entities/{id}/neighbors, /api/graph/subgraph/{id}, /api/graph/document/{id},
  /api/health/neo4j)
"""

from typing import Any, Dict, List, Optional
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.client import Neo4jClient, get_neo4j_client, set_neo4j_client
from app.graph.queries import (
    ALLOWED_GRAPH_RELATIONSHIP_TYPES,
    FALLBACK_RELATIONSHIP_TYPE,
    build_merge_relationship_query,
    sanitize_relationship_type,
)
from app.graph.repository import GraphRepository
from app.graph.schemas import (
    GraphEdge,
    GraphEntityDetailResponse,
    GraphHealthResponse,
    GraphNeighborsResponse,
    GraphNode,
    GraphSyncResponse,
    SubgraphResponse,
)
from app.graph.sync_service import GraphSyncService
from app.models.document import Document, DocumentChunk, generate_uuid_str
from app.models.entity import ChunkEntity, Entity
from app.models.relationship import EntityRelationship


# ── Mock Neo4j Client ──────────────────────────────────────────────────────────


class MockNeo4jClient(Neo4jClient):
    """Deterministic mock for Neo4jClient that records queries and returns configurable results."""

    def __init__(self, healthy: bool = True) -> None:
        super().__init__()
        self.healthy = healthy
        self.executed_queries: List[Dict[str, Any]] = []
        self._connected = healthy
        self.mock_entities: List[Dict[str, Any]] = []
        self.mock_edges: List[Dict[str, Any]] = []

    async def connect(self) -> bool:
        return self.healthy

    async def close(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if not self.healthy:
            raise ConnectionError("Mock Neo4j unreachable")

        params = parameters or {}
        self.executed_queries.append({"query": query, "parameters": params})

        # Node count query
        if "count(n) AS node_count" in query:
            return [{"node_count": len(self.mock_entities)}]

        # Relationship count query
        if "count(r) AS rel_count" in query:
            return [{"rel_count": len(self.mock_edges)}]

        # Search entities query
        if "MATCH (e:Entity)" in query and "$q" in query:
            q_term = (params.get("q") or "").lower()
            results = []
            for item in self.mock_entities:
                cname = (item.get("canonical_name") or "").lower()
                dname = (item.get("display_name") or "").lower()
                if not q_term or q_term in cname or q_term in dname:
                    results.append({"e": item})
            return results[: params.get("limit", 20)]

        # Get single entity by ID query
        if ("RETURN e" in query or "return e" in query.lower()) and "MATCH (e:Entity {id: $id})" in query and "MENTIONED_IN" not in query:
            target_id = params.get("id")
            for item in self.mock_entities:
                if item.get("id") == target_id:
                    return [{"e": item}]
            return []

        # Outgoing edges query
        if "MATCH (s:Entity {id: $id})-[r]->(t:Entity)" in query:
            target_id = params.get("id")
            results = []
            for edge in self.mock_edges:
                if edge.get("source") == target_id:
                    results.append({
                        "r": edge,
                        "t": {"id": edge.get("target"), "display_name": edge.get("target")},
                        "rel_type": edge.get("type", "RELATED_TO"),
                    })
            return results

        # Incoming edges query
        if "MATCH (s:Entity)-[r]->(t:Entity {id: $id})" in query:
            target_id = params.get("id")
            results = []
            for edge in self.mock_edges:
                if edge.get("target") == target_id:
                    results.append({
                        "r": edge,
                        "s": {"id": edge.get("source"), "display_name": edge.get("source")},
                        "rel_type": edge.get("type", "RELATED_TO"),
                    })
            return results

        # Provenance document query
        if "-[:MENTIONED_IN]->" in query and "-[:PART_OF]->" in query:
            return [{
                "doc_id": "test-doc-123",
                "filename": "test-file.pdf",
                "mention_count": 3,
            }]

        # Subgraph query (APOC or fallback): nodes, relationships
        if "path_nodes AS n" in query or "doc_entities[..$max_nodes]" in query:
            return [{
                "nodes": self.mock_entities,
                "relationships": [
                    {
                        "id": edge.get("id"),
                        "source_entity_id": edge.get("source"),
                        "target_entity_id": edge.get("target"),
                        "relationship_type": edge.get("type", "RELATED_TO"),
                        "confidence": edge.get("confidence", 1.0),
                        "evidence_text": edge.get("evidence_text"),
                        "document_id": edge.get("document_id"),
                        "chunk_id": edge.get("chunk_id"),
                    }
                    for edge in self.mock_edges
                ],
            }]

        # Neighbors query: node_list, rel_list
        if "UNWIND ns AS n" in query:
            return [{
                "node_list": self.mock_entities,
                "rel_list": [
                    {
                        "id": edge.get("id"),
                        "source_entity_id": edge.get("source"),
                        "target_entity_id": edge.get("target"),
                        "relationship_type": edge.get("type", "RELATED_TO"),
                        "confidence": edge.get("confidence", 1.0),
                        "evidence_text": edge.get("evidence_text"),
                        "document_id": edge.get("document_id"),
                        "chunk_id": edge.get("chunk_id"),
                    }
                    for edge in self.mock_edges
                ],
            }]

        # Default empty return for mutations (MERGE, CREATE INDEX, etc.)
        return []

    async def execute_write_transaction(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Any:
        return await self.execute_query(query, parameters, database)

    async def check_health(self) -> Dict[str, Any]:
        if not self.healthy:
            return {
                "status": "unhealthy",
                "database": self._database,
                "connected": False,
                "error": "Cannot connect to Neo4j instance",
            }
        return {
            "status": "healthy",
            "database": self._database,
            "connected": True,
            "node_count": len(self.mock_entities),
            "relationship_count": len(self.mock_edges),
        }


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_neo4j():
    """Configure MockNeo4jClient with sample entities and edges."""
    client = MockNeo4jClient(healthy=True)
    client.mock_entities = [
        {
            "id": "ent-alice-1",
            "canonical_name": "Alice Smith",
            "display_name": "Alice Smith",
            "entity_type": "PERSON",
            "description": "Lead Principal Engineer",
        },
        {
            "id": "ent-acme-2",
            "canonical_name": "Acme Corp",
            "display_name": "Acme Corporation",
            "entity_type": "ORGANIZATION",
            "description": "Enterprise Technology Partner",
        },
        {
            "id": "ent-phoenix-3",
            "canonical_name": "Project Phoenix",
            "display_name": "Project Phoenix",
            "entity_type": "PROJECT",
            "description": "Core Event Federation Engine",
        },
    ]
    client.mock_edges = [
        {
            "id": "rel-1",
            "source": "ent-alice-1",
            "target": "ent-acme-2",
            "type": "WORKS_FOR",
            "confidence": 0.95,
            "evidence_text": "Alice Smith works for Acme Corp.",
            "document_id": "test-doc-123",
            "chunk_id": "chunk-1",
        },
        {
            "id": "rel-2",
            "source": "ent-acme-2",
            "target": "ent-phoenix-3",
            "type": "OWNS",
            "confidence": 0.92,
            "evidence_text": "Acme Corp owns and operates Project Phoenix.",
            "document_id": "test-doc-123",
            "chunk_id": "chunk-2",
        },
    ]

    set_neo4j_client(client)
    yield client
    set_neo4j_client(None)


# ── 1. Query & Sanitization Tests ─────────────────────────────────────────────


def test_sanitize_relationship_type_canonical():
    """Verify that canonical relationship types are preserved as uppercase."""
    assert sanitize_relationship_type("WORKS_FOR") == "WORKS_FOR"
    assert sanitize_relationship_type("works_for") == "WORKS_FOR"
    assert sanitize_relationship_type("OWNS") == "OWNS"
    assert sanitize_relationship_type("USES") == "USES"
    assert sanitize_relationship_type("PART_OF") == "PART_OF"
    assert sanitize_relationship_type("MENTIONED_IN") == "MENTIONED_IN"


def test_sanitize_relationship_type_injection_prevention():
    """Verify that invalid types or injection attempts are safely replaced with fallback."""
    # Attempt Cypher injection
    malicious = "WORKS_FOR]->() DELETE n; MATCH (x)-[r:"
    assert sanitize_relationship_type(malicious) == FALLBACK_RELATIONSHIP_TYPE

    # Types with special characters or spaces
    assert sanitize_relationship_type("CUSTOM REL") == FALLBACK_RELATIONSHIP_TYPE
    assert sanitize_relationship_type("UNKNOWN_TYPE_123") == FALLBACK_RELATIONSHIP_TYPE
    assert sanitize_relationship_type("") == FALLBACK_RELATIONSHIP_TYPE


def test_build_merge_relationship_query_safety():
    """Verify that dynamically constructed MERGE query contains sanitized type."""
    query = build_merge_relationship_query("WORKS_FOR")
    assert "[r:WORKS_FOR {" in query

    # Passing arbitrary untrusted string must use FALLBACK_RELATIONSHIP_TYPE
    untrusted_query = build_merge_relationship_query("DELETE *; DROP TABLE")
    assert f"[r:{FALLBACK_RELATIONSHIP_TYPE} {{" in untrusted_query


# ── 2. GraphRepository Tests ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_repository_search_entities(mock_neo4j: MockNeo4jClient):
    """Test searching entities by name substring."""
    repo = GraphRepository(client=mock_neo4j)
    results = await repo.search_entities("Alice")

    assert len(results) == 1
    assert results[0].canonical_name == "Alice Smith"
    assert results[0].entity_type == "PERSON"


@pytest.mark.asyncio
async def test_repository_get_entity(mock_neo4j: MockNeo4jClient):
    """Test retrieving a single entity by ID."""
    repo = GraphRepository(client=mock_neo4j)
    entity = await repo.get_entity("ent-alice-1")

    assert entity is not None
    assert entity.id == "ent-alice-1"
    assert entity.display_name == "Alice Smith"

    # Non-existent ID returns None
    missing = await repo.get_entity("non-existent-id")
    assert missing is None


@pytest.mark.asyncio
async def test_repository_get_entity_detail(mock_neo4j: MockNeo4jClient):
    """Test retrieving full entity details with incoming, outgoing, and provenance."""
    repo = GraphRepository(client=mock_neo4j)
    detail = await repo.get_entity_detail("ent-alice-1")

    assert detail is not None
    assert detail.entity.id == "ent-alice-1"
    assert len(detail.outgoing) == 1
    assert detail.outgoing[0].target == "ent-acme-2"
    assert detail.outgoing[0].type == "WORKS_FOR"
    assert len(detail.documents) == 1
    assert detail.documents[0].filename == "test-file.pdf"


@pytest.mark.asyncio
async def test_repository_get_neighbors(mock_neo4j: MockNeo4jClient):
    """Test retrieving 1-hop graph neighbors for an entity."""
    repo = GraphRepository(client=mock_neo4j)
    neighbors = await repo.get_entity_neighbors("ent-alice-1", depth=1)

    assert neighbors.entity_id == "ent-alice-1"
    assert len(neighbors.nodes) >= 2
    assert len(neighbors.edges) >= 1


@pytest.mark.asyncio
async def test_repository_get_subgraph(mock_neo4j: MockNeo4jClient):
    """Test retrieving bounded entity subgraph."""
    repo = GraphRepository(client=mock_neo4j)
    subgraph = await repo.get_subgraph("ent-alice-1", depth=2, max_nodes=50)

    assert len(subgraph.nodes) >= 2
    assert len(subgraph.edges) >= 1
    assert subgraph.truncated is False


@pytest.mark.asyncio
async def test_repository_get_document_subgraph(mock_neo4j: MockNeo4jClient):
    """Test retrieving document-scoped subgraph."""
    repo = GraphRepository(client=mock_neo4j)
    subgraph = await repo.get_document_subgraph("test-doc-123", max_nodes=50)

    assert len(subgraph.nodes) >= 2
    assert len(subgraph.edges) >= 1


# ── 3. GraphSyncService Tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sync_service_full_and_document_sync(
    db_session: AsyncSession, mock_neo4j: MockNeo4jClient
):
    """Test synchronizing PostgreSQL documents, chunks, entities, and relationships to Neo4j."""
    # 1. Create Document in PostgreSQL
    doc = Document(
        id=generate_uuid_str(),
        filename="company_overview.pdf",
        original_filename="company_overview.pdf",
        storage_path="data/uploads/company_overview.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        file_size=2048,
        status="processed",
    )
    db_session.add(doc)
    await db_session.flush()

    # 2. Create Chunk
    chunk = DocumentChunk(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_index=0,
        content="Alice Smith leads Engineering at Acme Corp.",
        token_count=12,
        char_count=43,
    )
    db_session.add(chunk)
    await db_session.flush()

    # 3. Create Entities
    ent_alice = Entity(
        id=generate_uuid_str(),
        canonical_name="Alice Smith",
        display_name="Alice Smith",
        entity_type="PERSON",
    )
    ent_acme = Entity(
        id=generate_uuid_str(),
        canonical_name="Acme Corp",
        display_name="Acme Corp",
        entity_type="ORGANIZATION",
    )
    db_session.add_all([ent_alice, ent_acme])
    await db_session.flush()

    # 4. Create Mentions (ChunkEntity)
    mention_alice = ChunkEntity(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_id=chunk.id,
        entity_id=ent_alice.id,
        mention_text="Alice Smith",
        start_char=0,
        end_char=11,
        confidence=0.98,
    )
    mention_acme = ChunkEntity(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_id=chunk.id,
        entity_id=ent_acme.id,
        mention_text="Acme Corp",
        start_char=33,
        end_char=42,
        confidence=0.96,
    )
    db_session.add_all([mention_alice, mention_acme])
    await db_session.flush()

    # 5. Create Relationship
    rel = EntityRelationship(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_id=chunk.id,
        source_entity_id=ent_alice.id,
        target_entity_id=ent_acme.id,
        relationship_type="WORKS_FOR",
        confidence=0.95,
        evidence_text="Alice Smith leads Engineering at Acme Corp.",
    )
    db_session.add(rel)
    await db_session.commit()

    # Run GraphSyncService
    sync_service = GraphSyncService(client=mock_neo4j, db=db_session)

    # Document-scoped sync
    doc_res = await sync_service.sync_document(document_id=doc.id, db=db_session)
    assert doc_res.documents_synced == 1
    assert doc_res.chunks_synced == 1
    assert doc_res.entities_synced == 2
    assert doc_res.mentions_synced == 2
    assert doc_res.relationships_synced == 1
    assert doc_res.errors == 0

    # Full sync
    full_res = await sync_service.sync_all(db=db_session)
    assert full_res.documents_synced >= 1
    assert full_res.entities_synced >= 2
    assert full_res.relationships_synced >= 1
    assert full_res.errors == 0


# ── 4. API Endpoints Tests ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_health_neo4j(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/health/neo4j endpoint."""
    res = await client.get("/api/health/neo4j")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["connected"] is True
    assert "node_count" in data


@pytest.mark.asyncio
async def test_api_graph_sync(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test POST /api/graph/sync endpoint."""
    res = await client.post("/api/graph/sync")
    assert res.status_code == 200
    data = res.json()
    assert "documents_synced" in data
    assert "entities_synced" in data
    assert "relationships_synced" in data
    assert data["errors"] == 0


@pytest.mark.asyncio
async def test_api_graph_entities_search(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/graph/entities/search endpoint."""
    res = await client.get("/api/graph/entities/search?q=Alice")
    assert res.status_code == 200
    nodes = res.json()
    assert isinstance(nodes, list)
    assert len(nodes) == 1
    assert nodes[0]["canonical_name"] == "Alice Smith"


@pytest.mark.asyncio
async def test_api_graph_entity_detail(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/graph/entities/{id} endpoint."""
    res = await client.get("/api/graph/entities/ent-alice-1")
    assert res.status_code == 200
    detail = res.json()
    assert detail["entity"]["id"] == "ent-alice-1"
    assert len(detail["outgoing"]) == 1
    assert detail["outgoing"][0]["type"] == "WORKS_FOR"


@pytest.mark.asyncio
async def test_api_graph_entity_neighbors(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/graph/entities/{id}/neighbors endpoint."""
    res = await client.get("/api/graph/entities/ent-alice-1/neighbors?depth=1")
    assert res.status_code == 200
    data = res.json()
    assert data["entity_id"] == "ent-alice-1"
    assert "nodes" in data
    assert "edges" in data


@pytest.mark.asyncio
async def test_api_graph_subgraph(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/graph/subgraph/ent-alice-1?depth=2 endpoint."""
    res = await client.get("/api/graph/subgraph/ent-alice-1?depth=2")
    assert res.status_code == 200
    subgraph = res.json()
    assert "nodes" in subgraph
    assert "edges" in subgraph
    assert "truncated" in subgraph


@pytest.mark.asyncio
async def test_api_graph_document_subgraph(client: AsyncClient, mock_neo4j: MockNeo4jClient):
    """Test GET /api/graph/document/test-doc-123 endpoint."""
    res = await client.get("/api/graph/document/test-doc-123")
    assert res.status_code == 200
    subgraph = res.json()
    assert "nodes" in subgraph
    assert "edges" in subgraph
