"""Unit and integration tests for embedding generation, status, and reindexing."""

import math
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingConfigurationError
from app.embeddings.factory import set_embedding_provider
from app.embeddings.mock_provider import MockEmbeddingProvider
from app.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.embeddings.service import EmbeddingService
from app.models.document import ChunkEmbedding, Document, DocumentChunk


@pytest.fixture(autouse=True)
def mock_provider_env():
    """Ensure mock provider is set for test isolation."""
    provider = MockEmbeddingProvider(model_name="mock-text-embedding-3-small", dimensions=1536)
    set_embedding_provider(provider)
    yield provider
    set_embedding_provider(None)


@pytest.mark.asyncio
async def test_mock_embedding_provider_properties():
    """Verify mock provider generates normalized unit vectors of exact dimension."""
    provider = MockEmbeddingProvider(model_name="test-model", dimensions=1536)
    assert provider.model_name == "test-model"
    assert provider.dimensions == 1536

    vec = await provider.embed_query("Security compliance and access tokens")
    assert len(vec) == 1536
    # Vector must be unit normalized: ||v||_2 == 1.0
    norm = math.sqrt(sum(x * x for x in vec))
    assert pytest.approx(norm, 1e-4) == 1.0

    # Determinism: identical text yields identical vectors
    vec2 = await provider.embed_query("Security compliance and access tokens")
    assert vec == vec2


@pytest.mark.asyncio
async def test_openai_provider_config_validation():
    """Verify OpenAI provider raises error on missing or empty API key."""
    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(api_key="")

    with pytest.raises(EmbeddingConfigurationError):
        OpenAIEmbeddingProvider(api_key="   ")


@pytest.mark.asyncio
async def test_generate_document_embeddings_and_status(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test generating embeddings for document chunks and checking embedding status."""
    # 1. Create document and chunks
    doc = Document(
        id="emb-doc-1",
        filename="cybersecurity_handbook.txt",
        original_filename="cybersecurity_handbook.txt",
        file_type="txt",
        file_size=2048,
        department="Security",
        owner="CISO",
        status="processed",
        extraction_status="completed",
        total_chunks=2,
    )
    db_session.add(doc)
    await db_session.flush()

    chunk1 = DocumentChunk(
        id="emb-chk-1",
        document_id=doc.id,
        chunk_index=0,
        content="All passwords must be at least 16 characters long and changed every 90 days.",
        char_count=77,
        token_count=18,
        section_header="Password Policy",
    )
    chunk2 = DocumentChunk(
        id="emb-chk-2",
        document_id=doc.id,
        chunk_index=1,
        content="Multi-factor authentication (MFA) is strictly mandatory for all remote VPN logins.",
        char_count=82,
        token_count=19,
        section_header="MFA Policy",
    )
    db_session.add_all([chunk1, chunk2])
    await db_session.commit()

    # 2. Trigger embedding generation via API
    resp = await async_client.post(f"/api/documents/{doc.id}/embeddings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["document_id"] == doc.id
    assert data["status"] == "completed"
    assert data["total_chunks"] == 2
    assert data["embedded_chunks"] == 2
    assert "mock" in data["model"]

    # 3. Verify chunk embeddings persisted in DB
    emb_stmt = select(ChunkEmbedding).where(ChunkEmbedding.document_id == doc.id)
    emb_res = await db_session.execute(emb_stmt)
    embeddings = list(emb_res.scalars().all())
    assert len(embeddings) == 2
    assert embeddings[0].dimensions == 1536
    assert len(embeddings[0].content_hash) == 64

    # 4. Check DocumentEmbeddingStatus API
    status_resp = await async_client.get(f"/api/documents/{doc.id}/embedding-status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["embedding_status"] == "completed"
    assert status_data["total_chunks"] == 2
    assert status_data["embedded_chunks"] == 2
    assert status_data["is_up_to_date"] is True


@pytest.mark.asyncio
async def test_embedding_idempotency_content_hash(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Verify that unchanged chunks are not re-embedded when force=False."""
    doc = Document(
        id="emb-doc-idempotent",
        filename="notes.txt",
        original_filename="notes.txt",
        file_type="txt",
        file_size=500,
        department="Operations",
        owner="Admin",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    db_session.add(doc)
    await db_session.flush()

    chunk = DocumentChunk(
        id="emb-chk-idem-1",
        document_id=doc.id,
        chunk_index=0,
        content="Standard operating procedure for data backup routines.",
        char_count=54,
        token_count=12,
    )
    db_session.add(chunk)
    await db_session.commit()

    # Initial embedding
    resp1 = await async_client.post(f"/api/documents/{doc.id}/embeddings")
    assert resp1.status_code == 200

    emb1 = await db_session.scalar(
        select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk.id)
    )
    initial_updated_at = emb1.updated_at

    # Second call without force: should skip re-embedding
    resp2 = await async_client.post(f"/api/documents/{doc.id}/embeddings?force=false")
    assert resp2.status_code == 200
    emb2 = await db_session.scalar(
        select(ChunkEmbedding).where(ChunkEmbedding.chunk_id == chunk.id)
    )
    assert emb2.updated_at == initial_updated_at


@pytest.mark.asyncio
async def test_reindex_api_endpoint(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test reindexing endpoint across documents."""
    doc = Document(
        id="emb-doc-reindex",
        filename="compliance.txt",
        original_filename="compliance.txt",
        file_type="txt",
        file_size=1000,
        department="Legal",
        owner="Counsel",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    chunk = DocumentChunk(
        id="emb-chk-reindex",
        document_id=doc.id,
        chunk_index=0,
        content="All data processing complies with GDPR and CCPA directives.",
        char_count=59,
        token_count=14,
    )
    db_session.add_all([doc, chunk])
    await db_session.commit()

    reindex_resp = await async_client.post(
        "/api/embeddings/reindex",
        json={"force": True, "document_ids": [doc.id]},
    )
    assert reindex_resp.status_code == 200
    data = reindex_resp.json()
    assert data["total_documents"] == 1
    assert data["processed_documents"] == 1
    assert data["total_chunks_embedded"] == 1
    assert data["failed_documents"] == 0


@pytest.mark.asyncio
async def test_embedding_nonexistent_document_raises_404(async_client: AsyncClient):
    """Verify requesting embeddings for a non-existent document yields 404."""
    resp = await async_client.post("/api/documents/non-existent-uuid/embeddings")
    assert resp.status_code == 404
