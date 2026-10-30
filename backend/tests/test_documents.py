"""Comprehensive tests for document metadata CRUD endpoints and persistence."""

import pytest
from httpx import AsyncClient


SAMPLE_DOC_1 = {
    "filename": "security_policy_2026.pdf",
    "original_filename": "security_policy_2026.pdf",
    "file_type": "pdf",
    "file_size": 254800,
    "department": "Security",
    "owner": "Sarah Jenkins",
    "description": "Zero trust architecture and enterprise security standards",
    "version": "1.0",
}

SAMPLE_DOC_2 = {
    "filename": "q3_financial_results.docx",
    "original_filename": "q3_financial_results.docx",
    "file_type": "docx",
    "file_size": 512000,
    "department": "Finance",
    "owner": "David Miller",
    "description": "Quarterly enterprise earnings analysis and balance sheet",
    "version": "1.2",
}

SAMPLE_DOC_3 = {
    "filename": "engineering_runbook.txt",
    "original_filename": "engineering_runbook.txt",
    "file_type": "txt",
    "file_size": 45000,
    "department": "Engineering",
    "owner": "Marcus Vance",
    "description": "Production incident response protocols and disaster recovery",
    "version": "2.0",
}


@pytest.mark.asyncio
async def test_create_document(client: AsyncClient):
    """Test creating a new document metadata record."""
    response = await client.post("/api/documents", json=SAMPLE_DOC_1)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 36  # UUID length
    assert data["filename"] == SAMPLE_DOC_1["filename"]
    assert data["original_filename"] == SAMPLE_DOC_1["original_filename"]
    assert data["file_type"] == "pdf"
    assert data["file_size"] == 254800
    assert data["department"] == "Security"
    assert data["owner"] == "Sarah Jenkins"
    assert data["status"] == "uploaded"
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_document_validation_error(client: AsyncClient):
    """Test validation failure when required fields are missing."""
    invalid_doc = {
        "filename": "missing_required_fields.pdf",
        # missing original_filename, file_type, file_size, etc.
    }
    response = await client.post("/api/documents", json=invalid_doc)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_documents(client: AsyncClient):
    """Test listing documents with pagination."""
    await client.post("/api/documents", json=SAMPLE_DOC_1)
    await client.post("/api/documents", json=SAMPLE_DOC_2)
    await client.post("/api/documents", json=SAMPLE_DOC_3)

    # Fetch all
    response = await client.get("/api/documents")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["documents"]) == 3

    # Test pagination
    paginated_resp = await client.get("/api/documents?skip=1&limit=1")
    assert paginated_resp.status_code == 200
    paginated_data = paginated_resp.json()
    assert paginated_data["total"] == 3
    assert len(paginated_data["documents"]) == 1


@pytest.mark.asyncio
async def test_filter_documents(client: AsyncClient):
    """Test filtering documents by department, file_type, and search keyword."""
    await client.post("/api/documents", json=SAMPLE_DOC_1)
    await client.post("/api/documents", json=SAMPLE_DOC_2)
    await client.post("/api/documents", json=SAMPLE_DOC_3)

    # Filter by department
    sec_resp = await client.get("/api/documents?department=Security")
    assert sec_resp.status_code == 200
    sec_data = sec_resp.json()
    assert sec_data["total"] == 1
    assert sec_data["documents"][0]["department"] == "Security"

    # Filter by file type
    docx_resp = await client.get("/api/documents?file_type=docx")
    assert docx_resp.status_code == 200
    docx_data = docx_resp.json()
    assert docx_data["total"] == 1
    assert docx_data["documents"][0]["file_type"] == "docx"

    # Search keyword
    search_resp = await client.get("/api/documents?search=incident")
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert "runbook" in search_data["documents"][0]["filename"]


@pytest.mark.asyncio
async def test_get_document_by_id(client: AsyncClient):
    """Test retrieving document metadata by primary key ID."""
    create_resp = await client.post("/api/documents", json=SAMPLE_DOC_1)
    doc_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 200
    doc_data = get_resp.json()
    assert doc_data["id"] == doc_id
    assert doc_data["filename"] == SAMPLE_DOC_1["filename"]


@pytest.mark.asyncio
async def test_get_document_not_found(client: AsyncClient):
    """Test retrieving non-existent document ID returns 404."""
    response = await client.get("/api/documents/non-existent-uuid-999")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_update_document(client: AsyncClient):
    """Test partially updating document metadata."""
    create_resp = await client.post("/api/documents", json=SAMPLE_DOC_1)
    doc_id = create_resp.json()["id"]

    update_payload = {
        "status": "processed",
        "description": "Updated zero trust policy description",
        "version": "1.1",
    }
    patch_resp = await client.patch(f"/api/documents/{doc_id}", json=update_payload)
    assert patch_resp.status_code == 200
    updated_data = patch_resp.json()
    assert updated_data["status"] == "processed"
    assert updated_data["description"] == "Updated zero trust policy description"
    assert updated_data["version"] == "1.1"
    # Unchanged fields remain intact
    assert updated_data["filename"] == SAMPLE_DOC_1["filename"]


@pytest.mark.asyncio
async def test_update_document_invalid_status(client: AsyncClient):
    """Test validation reject on illegal status transitions."""
    create_resp = await client.post("/api/documents", json=SAMPLE_DOC_1)
    doc_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/documents/{doc_id}", json={"status": "invalid_status_value"})
    assert patch_resp.status_code == 422


@pytest.mark.asyncio
async def test_update_document_not_found(client: AsyncClient):
    """Test updating non-existent document returns 404."""
    patch_resp = await client.patch("/api/documents/non-existent-uuid", json={"status": "processed"})
    assert patch_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document(client: AsyncClient):
    """Test deleting document metadata."""
    create_resp = await client.post("/api/documents", json=SAMPLE_DOC_1)
    doc_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/documents/{doc_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json()["id"] == doc_id

    # Verify document no longer exists
    get_resp = await client.get(f"/api/documents/{doc_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client: AsyncClient):
    """Test deleting non-existent document returns 404."""
    delete_resp = await client.delete("/api/documents/non-existent-uuid")
    assert delete_resp.status_code == 404
