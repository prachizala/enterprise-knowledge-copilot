"""Tests for Step 8 — Relationship Extraction.

Comprehensive tests covering:
- Schemas & validation (self-references, offsets, confidence)
- Normalization & vocabulary mapping
- Entity resolution (exact, alias, normalized, unresolved)
- Mock provider extraction
- Idempotency & content hash caching
- Processing dependency (entity extraction required first)
- Persistence & incoming/outgoing traversals
- API endpoints (extract, status, list, entity relationships, search, detail)
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.entities.factory import set_entity_extraction_provider
from app.extraction.entities.mock_provider import MockEntityExtractionProvider
from app.extraction.entities.service import EntityExtractionService
from app.extraction.relationships.base import (
    RelationshipExtractionError,
    RelationshipExtractionTimeoutError,
)
from app.extraction.relationships.normalization import normalize_relationship_type
from app.extraction.relationships.provider import (
    MockRelationshipExtractionProvider,
    set_relationship_extraction_provider,
)
from app.extraction.relationships.registry import (
    FALLBACK_RELATIONSHIP_TYPE,
    RELATIONSHIP_TYPES,
    is_symmetric_relationship,
    is_valid_relationship_type,
)
from app.extraction.relationships.schemas import (
    ExtractedRelationship,
    RelationshipExtractionStats,
)
from app.extraction.relationships.service import RelationshipExtractionService
from app.models.document import Document, DocumentChunk, generate_uuid_str
from app.models.entity import ChunkEntity, Entity
from app.models.relationship import EntityRelationship


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def use_mock_providers():
    """Inject deterministic mock providers for entities and relationships during tests."""
    ent_provider = MockEntityExtractionProvider()
    set_entity_extraction_provider(ent_provider)

    rel_provider = MockRelationshipExtractionProvider()
    set_relationship_extraction_provider(rel_provider)

    yield

    set_entity_extraction_provider(None)
    set_relationship_extraction_provider(None)


@pytest_asyncio.fixture
async def document_with_entities(db_session: AsyncSession) -> Document:
    """Create a document with chunks and pre-extracted entities."""
    doc = Document(
        id=generate_uuid_str(),
        filename="test_corp_handbook.pdf",
        original_filename="test_corp_handbook.pdf",
        file_type="pdf",
        file_size=2048,
        department="Engineering",
        owner="Lead Architect",
        status="processed",
        extraction_status="completed",
        total_chunks=2,
    )
    db_session.add(doc)
    await db_session.flush()

    chunk1 = DocumentChunk(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_index=0,
        content="Alice Johnson works for Acme Corporation and manages the Platform Engineering team.",
        char_count=85,
        token_count=19,
        content_hash="hash_rel_chunk_0",
        section_header="Leadership",
    )
    chunk2 = DocumentChunk(
        id=generate_uuid_str(),
        document_id=doc.id,
        chunk_index=1,
        content="Project Phoenix uses PostgreSQL and is owned by Platform Engineering.",
        char_count=70,
        token_count=16,
        content_hash="hash_rel_chunk_1",
        section_header="Architecture",
    )
    db_session.add_all([chunk1, chunk2])
    await db_session.flush()

    # Pre-create canonical entities
    e_alice = Entity(
        id=generate_uuid_str(),
        entity_type="PERSON",
        canonical_name="alice johnson",
        display_name="Alice Johnson",
    )
    e_acme = Entity(
        id=generate_uuid_str(),
        entity_type="ORGANIZATION",
        canonical_name="acme corporation",
        display_name="Acme Corporation",
    )
    e_dept = Entity(
        id=generate_uuid_str(),
        entity_type="DEPARTMENT",
        canonical_name="platform engineering",
        display_name="Platform Engineering",
    )
    e_proj = Entity(
        id=generate_uuid_str(),
        entity_type="PROJECT",
        canonical_name="project phoenix",
        display_name="Project Phoenix",
    )
    e_tech = Entity(
        id=generate_uuid_str(),
        entity_type="TECHNOLOGY",
        canonical_name="postgresql",
        display_name="PostgreSQL",
    )
    db_session.add_all([e_alice, e_acme, e_dept, e_proj, e_tech])
    await db_session.flush()

    # Link chunk 1 entities
    ce1 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk1.id,
        entity_id=e_alice.id,
        document_id=doc.id,
        mention_text="Alice Johnson",
        confidence=0.98,
        start_char=0,
        end_char=13,
        content_hash=chunk1.content_hash,
    )
    ce2 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk1.id,
        entity_id=e_acme.id,
        document_id=doc.id,
        mention_text="Acme Corporation",
        confidence=0.95,
        start_char=24,
        end_char=40,
        content_hash=chunk1.content_hash,
    )
    ce3 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk1.id,
        entity_id=e_dept.id,
        document_id=doc.id,
        mention_text="Platform Engineering",
        confidence=0.90,
        start_char=57,
        end_char=77,
        content_hash=chunk1.content_hash,
    )

    # Link chunk 2 entities
    ce4 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk2.id,
        entity_id=e_proj.id,
        document_id=doc.id,
        mention_text="Project Phoenix",
        confidence=0.96,
        start_char=0,
        end_char=15,
        content_hash=chunk2.content_hash,
    )
    ce5 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk2.id,
        entity_id=e_tech.id,
        document_id=doc.id,
        mention_text="PostgreSQL",
        confidence=0.94,
        start_char=21,
        end_char=31,
        content_hash=chunk2.content_hash,
    )
    ce6 = ChunkEntity(
        id=generate_uuid_str(),
        chunk_id=chunk2.id,
        entity_id=e_dept.id,
        document_id=doc.id,
        mention_text="Platform Engineering",
        confidence=0.91,
        start_char=48,
        end_char=68,
        content_hash=chunk2.content_hash,
    )

    db_session.add_all([ce1, ce2, ce3, ce4, ce5, ce6])
    doc.entity_extraction_status = "completed"
    doc.unique_entity_count = 5
    doc.entity_mention_count = 6
    await db_session.commit()
    await db_session.refresh(doc)
    return doc


# ── Unit tests: Registry & Normalization ─────────────────────────────────────


def test_registry_contains_enterprise_types():
    assert "WORKS_FOR" in RELATIONSHIP_TYPES
    assert "MANAGES" in RELATIONSHIP_TYPES
    assert "REPORTS_TO" in RELATIONSHIP_TYPES
    assert "OWNS" in RELATIONSHIP_TYPES
    assert "USES" in RELATIONSHIP_TYPES
    assert "DEPENDS_ON" in RELATIONSHIP_TYPES
    assert "RELATED_TO" in RELATIONSHIP_TYPES
    assert len(RELATIONSHIP_TYPES) >= 25


def test_is_valid_relationship_type():
    assert is_valid_relationship_type("WORKS_FOR") is True
    assert is_valid_relationship_type("manages") is True
    assert is_valid_relationship_type("SUPER_SECRET_LINK") is False


def test_is_symmetric_relationship():
    assert is_symmetric_relationship("PARTNERS_WITH") is True
    assert is_symmetric_relationship("RELATED_TO") is True
    assert is_symmetric_relationship("WORKS_FOR") is False


def test_normalization_common_phrases():
    assert normalize_relationship_type("works for") == "WORKS_FOR"
    assert normalize_relationship_type("works-for") == "WORKS_FOR"
    assert normalize_relationship_type("employed by") == "WORKS_FOR"
    assert normalize_relationship_type("is responsible for managing") == "MANAGES"
    assert normalize_relationship_type("reports to") == "REPORTS_TO"
    assert normalize_relationship_type("part of") == "PART_OF"
    assert normalize_relationship_type("uses") == "USES"
    assert normalize_relationship_type("depends on") == "DEPENDS_ON"
    assert normalize_relationship_type("based in") == "LOCATED_IN"


def test_normalization_unknown_falls_back():
    assert normalize_relationship_type("invented_by_random_model") == FALLBACK_RELATIONSHIP_TYPE
    assert normalize_relationship_type("") == FALLBACK_RELATIONSHIP_TYPE
    assert normalize_relationship_type("   ") == FALLBACK_RELATIONSHIP_TYPE


# ── Unit tests: Schemas & Validation ─────────────────────────────────────────


def test_extracted_relationship_valid():
    rel = ExtractedRelationship(
        source_entity_text="Alice",
        relationship_type="works for",
        target_entity_text="Acme",
        confidence=0.95,
        evidence_text="Alice works for Acme.",
    )
    assert rel.relationship_type == "WORKS_FOR"
    assert rel.confidence == 0.95


def test_extracted_relationship_rejects_self_reference():
    with pytest.raises(ValueError, match="Self-referential"):
        ExtractedRelationship(
            source_entity_text="Acme",
            relationship_type="PARTNERS_WITH",
            target_entity_text="acme",
            confidence=0.9,
        )


def test_extracted_relationship_rejects_empty_endpoint():
    with pytest.raises(Exception):
        ExtractedRelationship(
            source_entity_text="",
            relationship_type="WORKS_FOR",
            target_entity_text="Acme",
            confidence=0.8,
        )


def test_extracted_relationship_rejects_invalid_offsets():
    with pytest.raises(ValueError, match="source_end_char must be greater"):
        ExtractedRelationship(
            source_entity_text="Alice",
            relationship_type="WORKS_FOR",
            target_entity_text="Acme",
            confidence=0.8,
            source_start_char=20,
            source_end_char=10,
        )


def test_extracted_relationship_confidence_bounds():
    with pytest.raises(Exception):
        ExtractedRelationship(
            source_entity_text="Alice",
            relationship_type="WORKS_FOR",
            target_entity_text="Acme",
            confidence=1.5,
        )


# ── Integration tests: Service & Persistence ────────────────────────────────


@pytest.mark.asyncio
async def test_dependency_enforced_no_entities_raises(db_session: AsyncSession):
    """Attempting relationship extraction before entity extraction raises ValueError."""
    doc = Document(
        id=generate_uuid_str(),
        filename="empty_doc.pdf",
        original_filename="empty_doc.pdf",
        file_type="pdf",
        file_size=100,
        department="General",
        owner="Tester",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    db_session.add(doc)
    await db_session.commit()

    with pytest.raises(ValueError, match="Run entity extraction first"):
        await RelationshipExtractionService.extract_document_relationships(
            db=db_session, document_id=doc.id
        )


@pytest.mark.asyncio
async def test_extract_relationships_success(
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """Full relationship extraction pipeline extracts and persists relationships."""
    stats = await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )

    assert stats.total_chunks == 2
    assert stats.processed_chunks == 2
    assert stats.relationships_found > 0
    assert stats.relationships_created > 0
    assert stats.failed_chunks == 0

    # Verify rows in database
    rels_res = await db_session.execute(
        select(EntityRelationship).where(
            EntityRelationship.document_id == document_with_entities.id
        )
    )
    rels = rels_res.scalars().all()
    assert len(rels) == stats.relationships_created

    # Verify foreign keys and types
    for r in rels:
        assert r.source_entity_id is not None
        assert r.target_entity_id is not None
        assert r.relationship_type in RELATIONSHIP_TYPES
        assert r.chunk_id is not None
        assert r.document_id == document_with_entities.id
        assert r.confidence > 0.0
        assert r.evidence_text is not None

    # Check updated document status
    await db_session.refresh(document_with_entities)
    assert document_with_entities.relationship_extraction_status == "completed"
    assert document_with_entities.relationship_count == len(rels)


@pytest.mark.asyncio
async def test_extract_relationships_idempotent(
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """Re-running relationship extraction without force skips already-extracted chunks."""
    stats1 = await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )
    stats2 = await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )

    assert stats2.skipped == stats1.processed_chunks
    assert stats2.relationships_created == 0


@pytest.mark.asyncio
async def test_extract_relationships_force_reprocesses(
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """force=True re-evaluates all chunks."""
    await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )
    stats = await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id, force=True
    )
    assert stats.processed_chunks == 2


@pytest.mark.asyncio
async def test_entity_relationships_traversal(
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """get_entity_relationships returns incoming and outgoing relationships."""
    await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )

    # Find Alice
    alice_res = await db_session.execute(
        select(Entity).where(Entity.canonical_name == "alice johnson")
    )
    alice = alice_res.scalar_one()

    traversal = await RelationshipExtractionService.get_entity_relationships(
        db=db_session, entity_id=alice.id
    )

    assert traversal["entity_id"] == alice.id
    assert traversal["total_outgoing"] > 0
    assert len(traversal["outgoing"]) > 0

    # Ensure outgoing relationship has correct target
    out_rel = traversal["outgoing"][0]
    assert out_rel.source_entity.id == alice.id


@pytest.mark.asyncio
async def test_search_relationships(
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """search_relationships matches across entities, relationship types, and evidence."""
    await RelationshipExtractionService.extract_document_relationships(
        db=db_session, document_id=document_with_entities.id
    )

    # Search by entity name
    results, total = await RelationshipExtractionService.search_relationships(
        db=db_session, q="alice"
    )
    assert total >= 1
    assert any("alice" in r.source_entity.canonical_name.lower() for r in results)

    # Search by relationship type
    results, total = await RelationshipExtractionService.search_relationships(
        db=db_session, q="works_for"
    )
    assert total >= 1
    assert any(r.relationship_type == "WORKS_FOR" for r in results)


# ── API Endpoint Tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_extract_relationships_success(
    client: AsyncClient,
    document_with_entities: Document,
):
    """POST /api/documents/{id}/relationships/extract triggers extraction."""
    response = await client.post(
        f"/api/documents/{document_with_entities.id}/relationships/extract"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert "stats" in data
    assert data["stats"]["relationships_created"] > 0


@pytest.mark.asyncio
async def test_api_extract_relationships_missing_entities_400(
    client: AsyncClient,
    db_session: AsyncSession,
):
    """POST without pre-extracted entities returns 400 with helpful error."""
    doc = Document(
        id=generate_uuid_str(),
        filename="no_entities.pdf",
        original_filename="no_entities.pdf",
        file_type="pdf",
        file_size=100,
        department="IT",
        owner="Admin",
        status="processed",
    )
    db_session.add(doc)
    await db_session.commit()

    response = await client.post(f"/api/documents/{doc.id}/relationships/extract")
    assert response.status_code == 400
    assert "Run entity extraction first" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_extract_relationships_404(client: AsyncClient):
    response = await client.post("/api/documents/non-existent-doc-id/relationships/extract")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_relationship_status(
    client: AsyncClient,
    document_with_entities: Document,
):
    """GET /api/documents/{id}/relationships/status returns status."""
    response = await client.get(
        f"/api/documents/{document_with_entities.id}/relationships/status"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["document_id"] == document_with_entities.id
    assert "relationship_extraction_status" in data


@pytest.mark.asyncio
async def test_api_list_document_relationships(
    client: AsyncClient,
    document_with_entities: Document,
):
    """GET /api/documents/{id}/relationships returns list."""
    # Run extraction first
    await client.post(f"/api/documents/{document_with_entities.id}/relationships/extract")

    response = await client.get(
        f"/api/documents/{document_with_entities.id}/relationships"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["relationships"]) > 0
    rel = data["relationships"][0]
    assert "source_entity" in rel
    assert "target_entity" in rel
    assert "relationship_type" in rel


@pytest.mark.asyncio
async def test_api_entity_relationships(
    client: AsyncClient,
    document_with_entities: Document,
    db_session: AsyncSession,
):
    """GET /api/entities/{id}/relationships returns incoming and outgoing."""
    await client.post(f"/api/documents/{document_with_entities.id}/relationships/extract")

    alice = (await db_session.execute(
        select(Entity).where(Entity.canonical_name == "alice johnson")
    )).scalar_one()

    response = await client.get(f"/api/entities/{alice.id}/relationships")
    assert response.status_code == 200
    data = response.json()
    assert data["entity_id"] == alice.id
    assert "outgoing" in data
    assert "incoming" in data


@pytest.mark.asyncio
async def test_api_relationship_detail(
    client: AsyncClient,
    document_with_entities: Document,
):
    """GET /api/relationships/{id} returns single relationship."""
    await client.post(f"/api/documents/{document_with_entities.id}/relationships/extract")
    list_res = await client.get(f"/api/documents/{document_with_entities.id}/relationships")
    rel_id = list_res.json()["relationships"][0]["id"]

    response = await client.get(f"/api/relationships/{rel_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == rel_id
    assert data["relationship_type"] is not None


@pytest.mark.asyncio
async def test_api_relationship_search(
    client: AsyncClient,
    document_with_entities: Document,
):
    """GET /api/relationships/search requires q parameter."""
    err_res = await client.get("/api/relationships/search")
    assert err_res.status_code == 422

    await client.post(f"/api/documents/{document_with_entities.id}/relationships/extract")
    search_res = await client.get("/api/relationships/search?q=acme")
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 1
