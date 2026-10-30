"""Tests for Sparse BM25 Keyword Search and Tri-Hybrid Candidate Fusion."""

import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.retrieval.candidate_fusion import CandidateFusion
from app.retrieval.keyword_search import KeywordSearchService, tokenize
from app.retrieval.schemas import (
    GraphCandidate,
    GraphPath,
    SparseCandidate,
    VectorCandidate,
)


def test_tokenize_logic():
    text = "The ISO-27001 Security Policy requires MFA authentication and zero-trust!"
    tokens = tokenize(text)
    assert "iso-27001" in tokens
    assert "security" in tokens
    assert "policy" in tokens
    assert "mfa" in tokens
    assert "authentication" in tokens
    assert "zero-trust" in tokens
    assert "the" not in tokens
    assert "and" not in tokens


@pytest.mark.asyncio
async def test_keyword_search_bm25_scoring(db_session: AsyncSession):
    doc_id = str(uuid.uuid4())
    doc = Document(
        id=doc_id,
        filename="Security_Requirements.pdf",
        original_filename="Security_Requirements.pdf",
        file_type="pdf",
        file_size=1024,
        department="Security",
        owner="Admin",
        status="processed",
    )
    db_session.add(doc)

    chunk1 = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        chunk_index=0,
        content="Zero-trust network architecture requires MFA authentication for all engineering endpoints.",
        char_count=87,
        token_count=20,
    )
    chunk2 = DocumentChunk(
        id=str(uuid.uuid4()),
        document_id=doc_id,
        chunk_index=1,
        content="PostgreSQL database cluster backups are scheduled daily at midnight with encryption.",
        char_count=85,
        token_count=20,
    )
    db_session.add_all([chunk1, chunk2])
    await db_session.commit()

    candidates = await KeywordSearchService.search_candidates(
        db=db_session,
        query="MFA authentication zero-trust",
        top_k=5,
    )

    assert len(candidates) >= 1
    top_cand = candidates[0]
    assert top_cand.chunk_id == chunk1.id
    assert top_cand.bm25_score > 0.0
    assert "authentication" in top_cand.matched_terms or "zero-trust" in top_cand.matched_terms


@pytest.mark.asyncio
async def test_tri_hybrid_fusion(db_session: AsyncSession):
    chunk_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    vector_cand = VectorCandidate(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_title="Security.pdf",
        chunk_index=0,
        content="Zero-trust authentication and access controls.",
        similarity_score=0.88,
        department="Security",
    )

    sparse_cand = SparseCandidate(
        chunk_id=chunk_id,
        document_id=doc_id,
        document_title="Security.pdf",
        chunk_index=0,
        content="Zero-trust authentication and access controls.",
        bm25_score=0.92,
        matched_terms=["authentication", "zero-trust"],
        department="Security",
    )

    graph_cand = GraphCandidate(
        entity_id="ent-1",
        canonical_name="Zero-Trust",
        entity_type="POLICY",
        associated_chunk_ids=[chunk_id],
        associated_document_ids=[doc_id],
    )

    fused = await CandidateFusion.fuse(
        db=db_session,
        vector_candidates=[vector_cand],
        sparse_candidates=[sparse_cand],
        graph_candidates=[graph_cand],
        graph_paths=[],
    )

    assert len(fused) == 1
    cand = fused[0]
    assert cand.chunk_id == chunk_id
    assert cand.origin == "tri-hybrid"
    assert cand.vector_score == 0.88
    assert cand.sparse_score == 0.92
    assert cand.graph_score == 0.90
    assert "Zero-Trust" in cand.connected_entities
    assert cand.final_score > 0.80
