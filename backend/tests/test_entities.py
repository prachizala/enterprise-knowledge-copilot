"""Tests for Step 7 — Entity Extraction.

All tests use the deterministic MockEntityExtractionProvider via the
set_entity_extraction_provider() fixture. No real API key needed.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.extraction.entities.mock_provider import MockEntityExtractionProvider
from app.extraction.entities.factory import set_entity_extraction_provider
from app.extraction.entities.registry import (
    ENTITY_TYPES,
    ENTITY_TYPES_SORTED,
    is_valid_entity_type,
    normalize_entity_type,
)
from app.extraction.entities.schemas import ExtractedEntity
from app.extraction.entities.service import EntityExtractionService, _conservative_normalize
from app.models.document import Document, DocumentChunk, get_utc_now, generate_uuid_str
from app.models.entity import Entity, ChunkEntity


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def use_mock_entity_provider():
    """Inject deterministic mock provider for all entity tests."""
    provider = MockEntityExtractionProvider()
    set_entity_extraction_provider(provider)
    yield
    set_entity_extraction_provider(None)


@pytest_asyncio.fixture
async def sample_document(db_session: AsyncSession) -> Document:
    """Create a processed document with two chunks for entity extraction tests."""
    doc = Document(
        id=generate_uuid_str(),
        filename="test_entity_doc.pdf",
        original_filename="test_entity_doc.pdf",
        file_type="pdf",
        file_size=1234,
        department="Engineering",
        owner="Test User",
        status="processed",
        extraction_status="completed",
        total_chunks=2,
    )
    db_session.add(doc)
    await db_session.flush()

    chunks = [
        DocumentChunk(
            id=generate_uuid_str(),
            document_id=doc.id,
            chunk_index=0,
            content="Acme Corporation hired John Smith as Senior Engineer.",
            char_count=51,
            token_count=12,
            content_hash="hash_chunk_0",
        ),
        DocumentChunk(
            id=generate_uuid_str(),
            document_id=doc.id,
            chunk_index=1,
            content="The Engineering Department uses Python for Project Atlas.",
            char_count=57,
            token_count=13,
            content_hash="hash_chunk_1",
        ),
    ]
    db_session.add_all(chunks)
    await db_session.commit()
    return doc


# ── Unit tests: Registry ─────────────────────────────────────────────────────


def test_entity_types_not_empty():
    assert len(ENTITY_TYPES) > 0


def test_entity_types_sorted_matches_frozenset():
    assert set(ENTITY_TYPES_SORTED) == ENTITY_TYPES


def test_is_valid_entity_type_known():
    assert is_valid_entity_type("PERSON") is True
    assert is_valid_entity_type("ORGANIZATION") is True
    assert is_valid_entity_type("TECHNOLOGY") is True


def test_is_valid_entity_type_unknown():
    assert is_valid_entity_type("SPACECRAFT") is False
    assert is_valid_entity_type("") is False


def test_normalize_entity_type_known():
    assert normalize_entity_type("person") == "PERSON"
    assert normalize_entity_type("  organization  ") == "ORGANIZATION"


def test_normalize_entity_type_unknown_falls_back_to_other():
    assert normalize_entity_type("SPACECRAFT") == "OTHER"
    assert normalize_entity_type("spaceship") == "OTHER"


# ── Unit tests: Schemas ──────────────────────────────────────────────────────


def test_extracted_entity_valid():
    ent = ExtractedEntity(
        text="John Smith",
        type="PERSON",
        normalized_name="john smith",
        confidence=0.9,
    )
    assert ent.type == "PERSON"
    assert ent.normalized_name == "john smith"


def test_extracted_entity_type_normalized_to_uppercase():
    ent = ExtractedEntity(
        text="Acme Corp",
        type="organization",
        normalized_name="acme corp",
        confidence=0.8,
    )
    assert ent.type == "ORGANIZATION"


def test_extracted_entity_unknown_type_maps_to_other():
    ent = ExtractedEntity(
        text="XJ-7",
        type="WIDGET",
        normalized_name="xj-7",
        confidence=0.6,
    )
    assert ent.type == "OTHER"


def test_extracted_entity_invalid_confidence():
    with pytest.raises(Exception):
        ExtractedEntity(
            text="A",
            type="PERSON",
            normalized_name="a",
            confidence=1.5,  # > 1.0, invalid
        )


def test_extracted_entity_end_before_start_raises():
    with pytest.raises(Exception):
        ExtractedEntity(
            text="A",
            type="PERSON",
            normalized_name="a",
            confidence=0.9,
            start_char=10,
            end_char=5,  # end < start
        )


def test_extracted_entity_empty_text_raises():
    with pytest.raises(Exception):
        ExtractedEntity(
            text="",
            type="PERSON",
            normalized_name="",
            confidence=0.8,
        )


# ── Unit tests: Normalization ────────────────────────────────────────────────


def test_conservative_normalize_lowercases():
    assert _conservative_normalize("John Smith") == "john smith"


def test_conservative_normalize_collapses_spaces():
    assert _conservative_normalize("John   Smith") == "john smith"


def test_conservative_normalize_strips_trailing_punctuation():
    assert _conservative_normalize("Acme Corp.") == "acme corp"


def test_conservative_normalize_strips_whitespace():
    assert _conservative_normalize("  Acme  ") == "acme"


# ── Unit tests: Mock provider ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mock_provider_properties():
    provider = MockEntityExtractionProvider()
    assert provider.provider_name == "mock"
    assert provider.model_name == "mock-v1"


@pytest.mark.asyncio
async def test_mock_provider_returns_entities():
    provider = MockEntityExtractionProvider()
    result = await provider.extract_entities("some text content", metadata={})
    assert isinstance(result, list)
    assert len(result) >= 2
    for ent in result:
        assert "text" in ent
        assert "type" in ent
        assert "normalized_name" in ent
        assert "confidence" in ent
        assert 0.0 <= ent["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_mock_provider_deterministic():
    """Same input produces same output on repeated calls."""
    provider = MockEntityExtractionProvider()
    text = "Deterministic input text for entity extraction."
    result1 = await provider.extract_entities(text, metadata={})
    result2 = await provider.extract_entities(text, metadata={})
    assert result1 == result2


# ── Integration tests: EntityExtractionService ──────────────────────────────


@pytest.mark.asyncio
async def test_extract_document_entities_success(
    sample_document: Document,
    db_session: AsyncSession,
):
    """Entity extraction creates Entity and ChunkEntity rows."""
    stats = await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    assert stats.total_chunks == 2
    assert stats.processed_chunks == 2
    assert stats.skipped_chunks == 0
    assert stats.entities_found > 0
    assert stats.unique_entities >= 1

    # Check database rows
    entity_count = (await db_session.execute(select(Entity))).scalars().all()
    chunk_entity_count = (await db_session.execute(
        select(ChunkEntity).where(ChunkEntity.document_id == sample_document.id)
    )).scalars().all()

    assert len(entity_count) > 0
    assert len(chunk_entity_count) > 0


@pytest.mark.asyncio
async def test_extract_document_entities_idempotent(
    sample_document: Document,
    db_session: AsyncSession,
):
    """Re-running extraction without force skips already-processed chunks."""
    stats1 = await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    stats2 = await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    assert stats2.skipped_chunks == stats1.processed_chunks
    assert stats2.processed_chunks == 0


@pytest.mark.asyncio
async def test_extract_document_entities_force_reprocesses(
    sample_document: Document,
    db_session: AsyncSession,
):
    """force=True re-processes already-extracted chunks."""
    await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    stats = await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
        force=True,
    )
    assert stats.processed_chunks == 2


@pytest.mark.asyncio
async def test_extract_nonexistent_document_raises(db_session: AsyncSession):
    with pytest.raises(ValueError, match="not found"):
        await EntityExtractionService.extract_document_entities(
            db=db_session,
            document_id="00000000-0000-0000-0000-000000000000",
        )


@pytest.mark.asyncio
async def test_document_status_updated_after_extraction(
    sample_document: Document,
    db_session: AsyncSession,
):
    """Document.entity_extraction_status is updated after extraction."""
    await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    await db_session.refresh(sample_document)
    assert sample_document.entity_extraction_status == "completed"
    assert sample_document.entity_mention_count > 0
    assert sample_document.unique_entity_count >= 1


@pytest.mark.asyncio
async def test_get_document_entity_status(
    sample_document: Document,
    db_session: AsyncSession,
):
    result = await EntityExtractionService.get_document_entity_status(
        db=db_session,
        document_id=sample_document.id,
    )
    assert result is not None
    assert result["document_id"] == sample_document.id
    assert "entity_extraction_status" in result


@pytest.mark.asyncio
async def test_list_document_entities(
    sample_document: Document,
    db_session: AsyncSession,
):
    await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    entities, total = await EntityExtractionService.list_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    assert total > 0
    assert len(entities) > 0
    for ent in entities:
        assert "mention_text" in ent
        assert "entity_type" in ent
        assert "confidence" in ent


@pytest.mark.asyncio
async def test_search_entities(
    sample_document: Document,
    db_session: AsyncSession,
):
    await EntityExtractionService.extract_document_entities(
        db=db_session,
        document_id=sample_document.id,
    )
    results, total = await EntityExtractionService.search_entities(
        db=db_session, q="acme"
    )
    assert total >= 1
    assert any("acme" in r["canonical_name"] for r in results)


# ── API endpoint tests ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_api_extract_entities_404(client: AsyncClient):
    response = await client.post(
        "/api/documents/00000000-0000-0000-0000-000000000000/entities/extract"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_entity_status_404(client: AsyncClient):
    response = await client.get(
        "/api/documents/00000000-0000-0000-0000-000000000000/entities/status"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_api_entity_search_requires_q(client: AsyncClient):
    response = await client.get("/api/entities/search")
    assert response.status_code == 422  # q is required


@pytest.mark.asyncio
async def test_api_entity_detail_404(client: AsyncClient):
    response = await client.get("/api/entities/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
