"""Tests for Structure-Aware Chunking, Metadata Provenance, Persistence, and Chunk APIs."""

import io
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.chunker import StructureAwareChunker, TextChunker
from app.models.document import Document, DocumentChunk


# --- Unit Tests for Structure-Aware Chunker ---

def test_structure_aware_chunker_pdf_page_provenance():
    """Verify that PDF page boundaries are accurately identified and assigned to chunks."""
    text = (
        "Page 1\n"
        "---------\n"
        "Introduction to Enterprise Knowledge Copilot.\n"
        "This platform connects enterprise knowledge stores with GraphRAG retrieval.\n\n"
        "Page 2\n"
        "---------\n"
        "Architecture Overview.\n"
        "The system incorporates vector search and knowledge graphs for precision.\n"
    )

    chunker = StructureAwareChunker(chunk_size=400, chunk_overlap=50)
    chunks = chunker.chunk_text(text=text, file_type="pdf")

    assert len(chunks) >= 2
    assert chunks[0].page_number == 1
    assert "Enterprise Knowledge Copilot" in chunks[0].content
    assert chunks[0].char_count == len(chunks[0].content)
    assert chunks[0].token_count > 0

    page_2_chunk = next(ch for ch in chunks if ch.page_number == 2)
    assert "Architecture Overview" in page_2_chunk.content
    assert page_2_chunk.page_number == 2


def test_structure_aware_chunker_headings_and_hierarchy():
    """Verify that markdown headings are extracted and tracked in section_header."""
    text = (
        "# Enterprise Security Policy\n"
        "All personnel must adhere to security controls.\n\n"
        "## Authentication Requirements\n"
        "Multi-factor authentication (MFA) is strictly mandatory for all services.\n\n"
        "### Password Standards\n"
        "Passwords must be at least 16 characters in length.\n"
    )

    chunker = StructureAwareChunker(chunk_size=500, chunk_overlap=50)
    chunks = chunker.chunk_text(text=text, file_type="docx")

    assert len(chunks) >= 2
    headers = [ch.section_header for ch in chunks if ch.section_header]
    assert any("Enterprise Security Policy" in h for h in headers)
    assert any("Authentication Requirements" in h for h in headers)


def test_structure_aware_chunker_table_preservation():
    """Verify that table blocks are recognized and tagged in chunk metadata."""
    text = (
        "# Database Configurations\n"
        "Here are the active connection configurations:\n\n"
        "[Table]\n"
        "Service | Host | Port | Status\n"
        "PostgreSQL | localhost | 5432 | Active\n"
        "Neo4j | localhost | 7687 | Standby\n"
    )

    chunker = StructureAwareChunker(chunk_size=600, chunk_overlap=50)
    chunks = chunker.chunk_text(text=text, file_type="docx")

    table_chunk = next((ch for ch in chunks if ch.metadata.get("is_table")), None)
    assert table_chunk is not None
    assert "PostgreSQL" in table_chunk.content
    assert "Neo4j" in table_chunk.content


def test_structure_aware_chunker_csv_record_grouping():
    """Verify that structured tabular records are grouped without slicing individual records."""
    text = (
        "[Record 1]\n"
        "Department: Engineering\n"
        "Role: Software Architect\n"
        "Location: Remote\n\n"
        "[Record 2]\n"
        "Department: Security\n"
        "Role: Security Officer\n"
        "Location: San Francisco\n"
    )

    chunker = StructureAwareChunker(chunk_size=800, chunk_overlap=50)
    chunks = chunker.chunk_text(text=text, file_type="csv")

    assert len(chunks) >= 1
    assert chunks[0].metadata.get("is_record_group") is True
    assert "Software Architect" in chunks[0].content
    assert "Security Officer" in chunks[0].content


# --- Integration Tests for Persistence and APIs ---

@pytest.mark.asyncio
async def test_upload_creates_persisted_chunks(client: AsyncClient, db_session: AsyncSession):
    """Uploading a document must process, chunk, and persist DocumentChunk rows in DB."""
    content = (
        "# Cloud Governance Policy\n\n"
        "This document details infrastructure policies and provisioning guidelines.\n\n"
        "## Storage Encryption\n"
        "All S3 buckets and PostgreSQL databases must enforce AES-256 encryption at rest.\n\n"
        "## Key Management\n"
        "Keys must be rotated automatically every 90 days using KMS.\n"
    ).encode("utf-8")

    response = await client.post(
        "/api/documents/upload",
        files={"file": ("Cloud_Governance.txt", io.BytesIO(content), "text/plain")},
        data={"department": "DevOps", "owner": "Dana Cloud"},
    )
    assert response.status_code == 201
    doc = response.json()
    doc_id = doc["id"]
    assert doc["status"] == "processed"
    assert doc["total_chunks"] >= 1

    # Verify chunks directly in database
    stmt = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    res = await db_session.execute(stmt)
    db_chunks_count = res.scalar_one()
    assert db_chunks_count == doc["total_chunks"]


@pytest.mark.asyncio
async def test_get_document_chunks_api(client: AsyncClient):
    """Test GET /api/documents/{id}/chunks returns structured chunks with pagination."""
    content = (
        "Page 1\n---------\n"
        + "Chapter 1: Foundations of Modern Distributed Computing.\n" * 10
        + "\n\nPage 2\n---------\n"
        + "Chapter 2: Fault Tolerance and Consensus Protocols.\n" * 10
    ).encode("utf-8")

    upload_res = await client.post(
        "/api/documents/upload",
        files={"file": ("Distributed_Systems.txt", io.BytesIO(content), "text/plain")},
        data={"department": "Architecture", "owner": "Prof. Turing"},
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["id"]

    # 1. Fetch all chunks
    chunks_res = await client.get(f"/api/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    data = chunks_res.json()
    assert data["document_id"] == doc_id
    assert data["total"] >= 2
    assert len(data["chunks"]) == data["total"]

    first_chunk = data["chunks"][0]
    assert first_chunk["chunk_index"] == 0
    assert first_chunk["char_count"] > 0
    assert first_chunk["token_count"] > 0
    assert first_chunk["page_number"] == 1

    # 2. Test Pagination
    page_res = await client.get(f"/api/documents/{doc_id}/chunks?skip=1&limit=1")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["total"] == data["total"]
    assert len(page_data["chunks"]) == 1
    assert page_data["chunks"][0]["chunk_index"] == 1

    # 3. Test Page Filter
    p2_res = await client.get(f"/api/documents/{doc_id}/chunks?page_number=2")
    assert p2_res.status_code == 200
    p2_data = p2_res.json()
    assert all(c["page_number"] == 2 for c in p2_data["chunks"])


@pytest.mark.asyncio
async def test_get_document_chunk_by_index(client: AsyncClient):
    """Test GET /api/documents/{id}/chunks/{chunk_index} retrieves specific chunk."""
    content = b"Short document for index test\n\nSecond paragraph content."
    upload_res = await client.post(
        "/api/documents/upload",
        files={"file": ("IndexTest.txt", io.BytesIO(content), "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    # Get index 0
    chunk_res = await client.get(f"/api/documents/{doc_id}/chunks/0")
    assert chunk_res.status_code == 200
    chunk = chunk_res.json()
    assert chunk["chunk_index"] == 0
    assert chunk["document_id"] == doc_id
    assert "Short document" in chunk["content"]

    # Get invalid index -> 404
    missing_res = await client.get(f"/api/documents/{doc_id}/chunks/999")
    assert missing_res.status_code == 404


@pytest.mark.asyncio
async def test_reprocessing_clears_old_chunks(client: AsyncClient, db_session: AsyncSession):
    """Reprocessing a document must clear previous chunks and regenerate fresh chunks without duplicates."""
    content = (
        "# Initial Version\n\n"
        "Paragraph one.\n\n"
        "Paragraph two.\n"
    ).encode("utf-8")

    upload_res = await client.post(
        "/api/documents/upload",
        files={"file": ("ReprocessTest.txt", io.BytesIO(content), "text/plain")},
    )
    doc_id = upload_res.json()["id"]
    initial_total = upload_res.json()["total_chunks"]

    # Reprocess document
    reprocess_res = await client.post(f"/api/documents/{doc_id}/process")
    assert reprocess_res.status_code == 200
    reprocessed_doc = reprocess_res.json()
    assert reprocessed_doc["status"] == "processed"
    assert reprocessed_doc["total_chunks"] == initial_total

    # Verify no duplicate chunks in database
    stmt = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    res = await db_session.execute(stmt)
    actual_db_count = res.scalar_one()
    assert actual_db_count == initial_total


@pytest.mark.asyncio
async def test_cascade_delete_removes_chunks(client: AsyncClient, db_session: AsyncSession):
    """Deleting a document must delete all its associated chunks from PostgreSQL."""
    content = b"# Document to delete\n\nSome important content that will be deleted."
    upload_res = await client.post(
        "/api/documents/upload",
        files={"file": ("ToDelete.txt", io.BytesIO(content), "text/plain")},
    )
    doc_id = upload_res.json()["id"]

    # Confirm chunks exist
    stmt = select(func.count()).select_from(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    res = await db_session.execute(stmt)
    assert res.scalar_one() > 0

    # Delete document
    del_res = await client.delete(f"/api/documents/{doc_id}")
    assert del_res.status_code == 200

    # Confirm chunks are gone
    res_after = await db_session.execute(stmt)
    assert res_after.scalar_one() == 0
