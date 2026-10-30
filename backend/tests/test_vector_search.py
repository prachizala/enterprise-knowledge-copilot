"""Integration tests for semantic vector search, metadata filtering, and provenance."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.factory import set_embedding_provider
from app.embeddings.mock_provider import MockEmbeddingProvider
from app.embeddings.service import EmbeddingService
from app.models.document import Document, DocumentChunk


@pytest.fixture(autouse=True)
def mock_provider_env():
    """Ensure mock provider is set for test isolation."""
    provider = MockEmbeddingProvider(model_name="mock-text-embedding-3-small", dimensions=1536)
    set_embedding_provider(provider)
    yield provider
    set_embedding_provider(None)


@pytest.mark.asyncio
async def test_semantic_vector_search_query_and_relevance(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test that natural language query returns the most semantically relevant chunks."""
    # 1. Create Security Document
    sec_doc = Document(
        id="vec-doc-sec",
        filename="infosec_standard.pdf",
        original_filename="infosec_standard.pdf",
        file_type="pdf",
        file_size=5000,
        department="Security",
        owner="Security Team",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    sec_chunk = DocumentChunk(
        id="vec-chk-sec-1",
        document_id=sec_doc.id,
        chunk_index=0,
        content="Enterprise access control requires multi-factor authentication (MFA) and biometric credentials.",
        char_count=98,
        token_count=22,
        page_number=3,
        section_header="Access Control > MFA",
    )

    # 2. Create Finance Document
    fin_doc = Document(
        id="vec-doc-fin",
        filename="q3_financial_results.csv",
        original_filename="q3_financial_results.csv",
        file_type="csv",
        file_size=8000,
        department="Finance",
        owner="CFO Office",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    fin_chunk = DocumentChunk(
        id="vec-chk-fin-1",
        document_id=fin_doc.id,
        chunk_index=0,
        content="Consolidated Q3 quarterly financial revenue increased by 24 percent with record EBITDA profits.",
        char_count=95,
        token_count=20,
        page_number=1,
        section_header="Quarterly Earnings",
    )

    db_session.add_all([sec_doc, sec_chunk, fin_doc, fin_chunk])
    await db_session.commit()

    # Generate embeddings for both
    await EmbeddingService.generate_document_embeddings(db=db_session, document_id=sec_doc.id)
    await EmbeddingService.generate_document_embeddings(db=db_session, document_id=fin_doc.id)

    # 3. Query matching Security
    sec_query_resp = await async_client.post(
        "/api/search/vector",
        json={
            "query": "authentication access control and multi-factor MFA credentials",
            "top_k": 5,
        },
    )
    assert sec_query_resp.status_code == 200
    sec_data = sec_query_resp.json()
    assert sec_data["total_results"] >= 1
    top_result = sec_data["results"][0]
    assert top_result["document_id"] == sec_doc.id
    assert top_result["section_header"] == "Access Control > MFA"
    assert top_result["page_number"] == 3
    assert top_result["similarity_score"] > 0.0
    assert 0.0 <= top_result["similarity_score"] <= 1.0

    # 4. Query matching Finance
    fin_query_resp = await async_client.post(
        "/api/search/vector",
        json={
            "query": "quarterly revenue and financial earnings profits",
            "top_k": 5,
        },
    )
    assert fin_query_resp.status_code == 200
    fin_data = fin_query_resp.json()
    assert fin_data["total_results"] >= 1
    top_fin_result = fin_data["results"][0]
    assert top_fin_result["document_id"] == fin_doc.id
    assert top_fin_result["file_type"] == "csv"


@pytest.mark.asyncio
async def test_vector_search_metadata_filtering(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test filtering search results by department, document_id, and file_type."""
    doc1 = Document(
        id="filter-doc-hr",
        filename="employee_handbook.docx",
        original_filename="employee_handbook.docx",
        file_type="docx",
        file_size=3000,
        department="Human Resources",
        owner="HR Admin",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    chk1 = DocumentChunk(
        id="filter-chk-1",
        document_id=doc1.id,
        chunk_index=0,
        content="Vacation policy permits 20 days paid annual leave for full-time employees.",
        char_count=73,
        token_count=16,
    )

    doc2 = Document(
        id="filter-doc-eng",
        filename="git_workflow.txt",
        original_filename="git_workflow.txt",
        file_type="txt",
        file_size=4000,
        department="Engineering",
        owner="Tech Lead",
        status="processed",
        extraction_status="completed",
        total_chunks=1,
    )
    chk2 = DocumentChunk(
        id="filter-chk-2",
        document_id=doc2.id,
        chunk_index=0,
        content="Feature branches must have passing automated unit tests before pull request merge.",
        char_count=82,
        token_count=18,
    )

    db_session.add_all([doc1, chk1, doc2, chk2])
    await db_session.commit()

    await EmbeddingService.generate_document_embeddings(db=db_session, document_id=doc1.id)
    await EmbeddingService.generate_document_embeddings(db=db_session, document_id=doc2.id)

    # Filter by department
    resp_hr = await async_client.post(
        "/api/search/vector",
        json={"query": "employee policy and workflow", "department": "Human Resources"},
    )
    assert resp_hr.status_code == 200
    results_hr = resp_hr.json()["results"]
    for r in results_hr:
        assert r["department"] == "Human Resources"
        assert r["document_id"] == doc1.id

    # Filter by document_id
    resp_doc = await async_client.post(
        "/api/search/vector",
        json={"query": "workflow tests merge", "document_id": doc2.id},
    )
    assert resp_doc.status_code == 200
    results_doc = resp_doc.json()["results"]
    for r in results_doc:
        assert r["document_id"] == doc2.id

    # Filter by file_type
    resp_ft = await async_client.post(
        "/api/search/vector",
        json={"query": "policy and testing", "file_type": "docx"},
    )
    assert resp_ft.status_code == 200
    results_ft = resp_ft.json()["results"]
    for r in results_ft:
        assert r["file_type"] == "docx"


@pytest.mark.asyncio
async def test_vector_search_top_k_and_threshold(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Test top_k limiting and similarity threshold behavior."""
    doc = Document(
        id="limits-doc",
        filename="multi_chunk.txt",
        original_filename="multi_chunk.txt",
        file_type="txt",
        file_size=2000,
        department="General",
        owner="Admin",
        status="processed",
        extraction_status="completed",
        total_chunks=3,
    )
    chunks = [
        DocumentChunk(
            id=f"lim-chk-{i}",
            document_id=doc.id,
            chunk_index=i,
            content=f"Paragraph {i} describing operational guidelines for system maintenance.",
            char_count=70,
            token_count=15,
        )
        for i in range(3)
    ]
    db_session.add(doc)
    db_session.add_all(chunks)
    await db_session.commit()

    await EmbeddingService.generate_document_embeddings(db=db_session, document_id=doc.id)

    # top_k = 1
    resp_top1 = await async_client.post(
        "/api/search/vector",
        json={"query": "operational guidelines maintenance", "top_k": 1},
    )
    assert resp_top1.status_code == 200
    data_top1 = resp_top1.json()
    assert len(data_top1["results"]) == 1

    # High threshold (e.g. 0.999) on dissimilar query should return 0 results
    resp_thresh = await async_client.post(
        "/api/search/vector",
        json={
            "query": "totally unrelated quantum mechanical astrophysics concept",
            "similarity_threshold": 0.999,
        },
    )
    assert resp_thresh.status_code == 200
    assert len(resp_thresh.json()["results"]) == 0
