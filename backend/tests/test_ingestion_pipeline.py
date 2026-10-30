"""Tests for Document Ingestion Pipeline Orchestrator and Jobs endpoints."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.services.document_service import document_service


@pytest.mark.asyncio
async def test_job_endpoints_flow(async_client: AsyncClient, db_session: AsyncSession):
    # 1. Create a document directly for testing
    doc = Document(
        filename="test_pipeline.txt",
        original_filename="test_pipeline.txt",
        file_type="txt",
        department="Engineering",
        owner="Alice",
        status="uploaded",
    )
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)

    # 2. Get latest job for document before any runs (returns null/None)
    latest_res = await async_client.get(f"/api/jobs/documents/{doc.id}/latest")
    assert latest_res.status_code == 200
    assert latest_res.json() is None

    # 3. Query non-existent job -> 404
    missing_res = await async_client.get("/api/jobs/non-existent-uuid")
    assert missing_res.status_code == 404
