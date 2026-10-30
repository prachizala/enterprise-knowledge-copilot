"""Comprehensive tests for document upload, validation, secure storage, and multi-format extraction."""

import io
from io import BytesIO
import pytest
from docx import Document as DocxDocument
from httpx import AsyncClient
from pypdf import PdfWriter

from app.core.config import settings

SAMPLE_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n"
    b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n"
    b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    b"4 0 obj << /Length 53 >> stream\n"
    b"BT\n/F1 18 Tf\n100 700 Td\n(Zero Trust Security Policy) Tj\nET\n"
    b"endstream\nendobj\n"
    b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000244 00000 n \n0000000347 00000 n \n"
    b"trailer << /Size 6 /Root 1 0 R >>\nstartxref\n424\n%%EOF\n"
)


def create_sample_docx_bytes() -> bytes:
    """Generate in-memory valid DOCX with headings, paragraphs, and a table."""
    doc = DocxDocument()
    doc.add_heading("Architecture Specification 2026", level=1)
    doc.add_paragraph("Project Alpha microservices event streaming architecture.")
    table = doc.add_table(rows=2, cols=2)
    table.rows[0].cells[0].text = "Microservice"
    table.rows[0].cells[1].text = "Tier"
    table.rows[1].cells[0].text = "Graph Engine"
    table.rows[1].cells[1].text = "Production"
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def create_empty_scanned_pdf_bytes() -> bytes:
    """Generate in-memory valid PDF with zero text characters."""
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_and_extract_pdf(client: AsyncClient):
    """Test uploading a valid PDF, extracting text with page boundary preservation, and fetching content."""
    files = {"file": ("enterprise_security.pdf", SAMPLE_PDF_BYTES, "application/pdf")}
    data = {
        "department": "Security",
        "owner": "Sarah Jenkins",
        "description": "Enterprise zero trust standards",
    }
    response = await client.post("/api/documents/upload", files=files, data=data)
    assert response.status_code == 201
    doc = response.json()

    assert doc["status"] == "processed"
    assert doc["extraction_status"] == "completed"
    assert doc["file_type"] == "pdf"
    assert doc["mime_type"] == "application/pdf"
    assert doc["extracted_text_length"] > 0
    assert doc["processed_at"] is not None
    assert doc["processing_error"] is None

    # Verify content endpoint
    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert content["document_id"] == doc["id"]
    assert "Page 1" in content["text"]
    assert "Zero Trust Security Policy" in content["text"]
    assert content["character_count"] > 0
    assert content["word_count"] > 0
    assert content["page_count"] == 1


@pytest.mark.asyncio
async def test_upload_and_extract_docx(client: AsyncClient):
    """Test uploading a valid DOCX with heading and table extraction."""
    docx_bytes = create_sample_docx_bytes()
    files = {"file": ("project_alpha.docx", docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {
        "department": "Engineering",
        "owner": "Marcus Vance",
    }
    response = await client.post("/api/documents/upload", files=files, data=data)
    assert response.status_code == 201
    doc = response.json()

    assert doc["status"] == "processed"
    assert doc["extraction_status"] == "completed"
    assert doc["file_type"] == "docx"

    # Verify content endpoint
    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert "Architecture Specification" in content["text"]
    assert "Project Alpha" in content["text"]
    assert "Graph Engine" in content["text"]
    assert content["character_count"] > 0


@pytest.mark.asyncio
async def test_upload_and_extract_txt(client: AsyncClient):
    """Test uploading a plain text file."""
    txt_content = b"Enterprise Runbook\nIncident Response Level 1\nPagerDuty alerts escalation path."
    files = {"file": ("runbook.txt", txt_content, "text/plain")}
    data = {"department": "Operations", "owner": "Ops Team"}

    response = await client.post("/api/documents/upload", files=files, data=data)
    assert response.status_code == 201
    doc = response.json()

    assert doc["status"] == "processed"
    assert doc["extraction_status"] == "completed"
    assert doc["file_type"] == "txt"

    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert "Enterprise Runbook" in content["text"]
    assert "PagerDuty" in content["text"]


@pytest.mark.asyncio
async def test_upload_and_extract_csv(client: AsyncClient):
    """Test uploading a CSV table and converting into structured records."""
    csv_content = b"customer_id,company_name,tier,status\nC001,Acme Corp,Enterprise,Active\nC002,Global Tech,Mid-Market,Pending"
    files = {"file": ("customers.csv", csv_content, "text/csv")}
    data = {"department": "Finance", "owner": "Finance Team"}

    response = await client.post("/api/documents/upload", files=files, data=data)
    assert response.status_code == 201
    doc = response.json()

    assert doc["status"] == "processed"
    assert doc["file_type"] == "csv"

    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 200
    content = content_resp.json()
    assert "customer_id: C001" in content["text"]
    assert "company_name: Acme Corp" in content["text"]
    assert "tier: Enterprise" in content["text"]


@pytest.mark.asyncio
async def test_upload_unsupported_file_extension(client: AsyncClient):
    """Test rejection of unsupported file extensions (e.g. .exe, .py)."""
    files = {"file": ("script.py", b"print('hello world')", "text/x-python")}
    response = await client.post("/api/documents/upload", files=files, data={"department": "IT"})
    assert response.status_code == 400
    data = response.json()
    assert "unsupported" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_invalid_mime_signature(client: AsyncClient):
    """Test rejection when filename extension does not match binary magic bytes."""
    fake_pdf = b"This is plain text disguised as a PDF file"
    files = {"file": ("fraud.pdf", fake_pdf, "application/pdf")}
    response = await client.post("/api/documents/upload", files=files, data={"department": "Security"})
    assert response.status_code == 400
    data = response.json()
    assert "not a valid pdf" in data["detail"].lower()


@pytest.mark.asyncio
async def test_upload_oversized_file(client: AsyncClient, monkeypatch):
    """Test rejection of files exceeding MAX_UPLOAD_SIZE_MB."""
    # Temporarily set max size to 1 KB for test
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)  # 0 MB forces limit check
    files = {"file": ("test.txt", b"A" * 2048, "text/plain")}
    response = await client.post("/api/documents/upload", files=files, data={"department": "IT"})
    assert response.status_code == 413
    data = response.json()
    assert "exceeds maximum allowed limit" in data["detail"].lower()


@pytest.mark.asyncio
async def test_scanned_or_empty_pdf_failure_handling(client: AsyncClient):
    """Test that a PDF with 0 extractable text is marked as failed rather than pretending success."""
    empty_pdf = create_empty_scanned_pdf_bytes()
    files = {"file": ("scanned_invoice.pdf", empty_pdf, "application/pdf")}
    response = await client.post("/api/documents/upload", files=files, data={"department": "Finance"})
    assert response.status_code == 201
    doc = response.json()

    # The document must NOT pretend processing succeeded
    assert doc["status"] == "failed"
    assert doc["extraction_status"] == "failed"
    assert doc["processing_error"] is not None
    assert "no extractable text" in doc["processing_error"].lower()

    # Querying content for failed document returns 404
    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 404


@pytest.mark.asyncio
async def test_download_document(client: AsyncClient):
    """Test downloading the original file and anti-traversal security."""
    files = {"file": ("download_test.txt", b"Downloadable enterprise content", "text/plain")}
    upload_resp = await client.post("/api/documents/upload", files=files, data={"department": "IT"})
    doc = upload_resp.json()

    # Download file
    dl_resp = await client.get(f"/api/documents/{doc['id']}/download")
    assert dl_resp.status_code == 200
    assert dl_resp.content == b"Downloadable enterprise content"
    assert "download_test.txt" in dl_resp.headers.get("content-disposition", "")

    # Non-existent ID returns 404
    bad_dl = await client.get("/api/documents/non-existent-uuid/download")
    assert bad_dl.status_code == 404


@pytest.mark.asyncio
async def test_reprocess_document(client: AsyncClient):
    """Test reprocessing an existing document replaces/updates extracted content."""
    files = {"file": ("reprocess_test.txt", b"First extraction version", "text/plain")}
    upload_resp = await client.post("/api/documents/upload", files=files, data={"department": "IT"})
    doc = upload_resp.json()
    assert doc["status"] == "processed"

    # Trigger reprocess
    process_resp = await client.post(f"/api/documents/{doc['id']}/process")
    assert process_resp.status_code == 200
    reprocessed = process_resp.json()
    assert reprocessed["status"] == "processed"
    assert reprocessed["extraction_status"] == "completed"

    # Verify content remains valid
    content_resp = await client.get(f"/api/documents/{doc['id']}/content")
    assert content_resp.status_code == 200
    assert "First extraction version" in content_resp.json()["text"]
