"""Document Ingestion API endpoints."""

from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.services.db import get_db
from app.models.document import DocumentModel, DocumentChunkModel
from app.ingestion.pipeline import IngestionPipeline
from app.schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentChunkResponse,
    DocumentUploadResponse,
)

router = APIRouter(prefix="/documents", tags=["Documents"])
pipeline = IngestionPipeline()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and ingest enterprise document",
    description="Uploads a PDF, DOCX, TXT, MD, or CSV file, performs text parsing, semantic chunking, and persists to storage.",
)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form("Engineering"),
    owner: str = Form("Alex Morgan"),
    db: Session = Depends(get_db),
) -> DocumentUploadResponse:
    """Accept an uploaded document file and trigger the parsing and chunking pipeline."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty.",
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    doc = pipeline.process_file_bytes(
        db=db,
        filename=file.filename,
        content_bytes=content,
        department=department,
        owner=owner,
    )

    return DocumentUploadResponse(
        message=f"Document '{doc.filename}' uploaded and parsed successfully.",
        document=DocumentResponse.model_validate(doc),
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List ingested enterprise documents",
    description="Retrieves ingested documents with optional filtering by department, file type, status, or search query.",
)
def list_documents(
    department: Optional[str] = Query(None, description="Filter by department"),
    file_type: Optional[str] = Query(None, description="Filter by file type (PDF, DOCX, etc.)"),
    status: Optional[str] = Query(None, description="Filter by status (PROCESSED, FAILED)"),
    search: Optional[str] = Query(None, description="Search by filename or owner"),
    skip: int = Query(0, ge=0, description="Pagination skip"),
    limit: int = Query(50, ge=1, le=100, description="Pagination limit"),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    """List documents with filtering and pagination."""
    query = db.query(DocumentModel)

    if department and department != "All":
        query = query.filter(DocumentModel.department == department)
    if file_type and file_type != "All":
        query = query.filter(DocumentModel.file_type == file_type.upper())
    if status and status != "All":
        query = query.filter(DocumentModel.status == status.upper())
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                DocumentModel.filename.ilike(search_pattern),
                DocumentModel.owner.ilike(search_pattern),
                DocumentModel.department.ilike(search_pattern),
            )
        )

    total = query.count()
    documents = (
        query.order_by(desc(DocumentModel.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return DocumentListResponse(
        total=total,
        documents=[DocumentResponse.model_validate(d) for d in documents],
    )


@router.get(
    "/{doc_id}",
    response_model=DocumentDetailResponse,
    summary="Get document details and chunks",
    description="Retrieves a specific document along with its extracted semantic chunks.",
)
def get_document(doc_id: str, db: Session = Depends(get_db)) -> DocumentDetailResponse:
    """Retrieve document metadata and all associated passages."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    chunks = (
        db.query(DocumentChunkModel)
        .filter(DocumentChunkModel.document_id == doc_id)
        .order_by(DocumentChunkModel.chunk_index)
        .all()
    )

    doc_response = DocumentDetailResponse.model_validate(doc)
    doc_response.chunks = [DocumentChunkResponse.model_validate(c) for c in chunks]
    return doc_response


@router.get(
    "/{doc_id}/chunks",
    response_model=List[DocumentChunkResponse],
    summary="Get document chunks",
    description="Returns all extracted passages and tokens for the given document.",
)
def get_document_chunks(
    doc_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[DocumentChunkResponse]:
    """Retrieve indexed passages for a given document."""
    doc = db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )

    chunks = (
        db.query(DocumentChunkModel)
        .filter(DocumentChunkModel.document_id == doc_id)
        .order_by(DocumentChunkModel.chunk_index)
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [DocumentChunkResponse.model_validate(c) for c in chunks]


@router.delete(
    "/{doc_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete document",
    description="Removes document and all associated chunks from storage and database.",
)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    """Delete document and all chunks."""
    deleted = pipeline.delete_document(db=db, doc_id=doc_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found.",
        )
    return {"message": f"Document '{doc_id}' and all associated chunks successfully deleted."}


@router.post(
    "/seed-demo",
    response_model=DocumentListResponse,
    summary="Seed demo enterprise documents",
    description="Populates realistic enterprise documents into the database if empty.",
)
def seed_demo_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    """Seed demo documents if none exist."""
    existing_count = db.query(DocumentModel).count()
    if existing_count > 0:
        docs = db.query(DocumentModel).order_by(desc(DocumentModel.created_at)).all()
        return DocumentListResponse(
            total=len(docs),
            documents=[DocumentResponse.model_validate(d) for d in docs],
        )

    demo_files = [
        (
            "Enterprise_Security_Policy_2026.md",
            """# Enterprise Security Policy 2026
## 1. Zero Trust Architecture
All enterprise systems, internal microservices, and external APIs must enforce zero-trust network segmentation. Mutual TLS (mTLS) with cryptographically verifiable x509 certificates is mandatory.

## 2. Cloud Infrastructure Standards
Cloud workloads deployed in AWS GovCloud or hybrid regions must utilize encrypted EBS volumes with customer-managed KMS keys. S3 buckets must enforce strict public access blocks and SSE-KMS encryption.

## 3. Data Retention and Privacy
Customer Personally Identifiable Information (PII) and audit event logs must be retained for seven years in compliance with SOC 2 Type II and ISO 27001 regulatory requirements. Unauthorized exfiltration triggers automated isolation.
""",
            "Security",
            "Sarah Jenkins",
        ),
        (
            "Project_Alpha_Architecture_Specification.md",
            """# Project Alpha: Event Streaming Architecture
## Executive Summary
Project Alpha delivers high-throughput event federation across enterprise microservices using Apache Kafka and FastAPI backends. The project is led by Marcus Vance (Director of Engineering).

## Infrastructure & Hosting
All service components run on AWS GovCloud within Kubernetes (EKS) clusters. Database persistence is managed via PostgreSQL Aurora clusters with multi-AZ failover.

## Dependencies and Governance
Project Alpha adheres to the 2026 Security Policy for data protection and integrates with the Enterprise Data Hub for real-time analytics.
""",
            "Engineering",
            "Marcus Vance",
        ),
        (
            "Customer_Architecture_Guide.txt",
            """Enterprise Customer Architecture Guide
Version: 3.4
Author: Elena Rostova

Overview:
This document specifies the target architecture for large enterprise customers deploying our knowledge reasoning platform.
Key systems include:
1. Neo4j Graph Database cluster hosting enterprise ontologies and relationship graphs.
2. PostgreSQL 16 cluster managing user authentication, document lineage, and audit trails.
3. High-dimensional vector store supporting reciprocal rank fusion hybrid retrieval.
High availability requires cross-region replication and automated health checks.
""",
            "Engineering",
            "Elena Rostova",
        ),
    ]

    for name, content, dept, owner in demo_files:
        pipeline.process_file_bytes(
            db=db,
            filename=name,
            content_bytes=content.encode("utf-8"),
            department=dept,
            owner=owner,
        )

    seeded_docs = db.query(DocumentModel).order_by(desc(DocumentModel.created_at)).all()
    return DocumentListResponse(
        total=len(seeded_docs),
        documents=[DocumentResponse.model_validate(d) for d in seeded_docs],
    )
