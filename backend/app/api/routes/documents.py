"""Document ingestion, validation, processing, and retrieval API endpoints."""

import logging
import uuid
from typing import Optional
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
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentContentResponse,
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    DocumentUpdate,
)
from app.embeddings.schemas import (
    DocumentEmbeddingStatusResponse,
    EmbeddingTaskResponse,
)
from app.embeddings.service import EmbeddingService
from app.extraction.entities.schemas import (
    ChunkEntityResponse,
    DocumentEntityStatusResponse,
    EntityExtractionTaskResponse,
)
from app.extraction.entities.service import EntityExtractionService
from app.extraction.entities.registry import ENTITY_TYPES_SORTED
from app.extraction.relationships.schemas import (
    DocumentRelationshipStatusResponse,
    RelationshipExtractionTaskResponse,
    RelationshipListResponse,
)
from app.extraction.relationships.service import RelationshipExtractionService
from app.services.document_service import document_service
from app.services.storage_service import (
    FileSizeExceededError,
    InvalidFileTypeError,
    StorageError,
    storage_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Process Document",
    description="Upload a PDF, DOCX, TXT, or CSV file. Validates size/type, safely stores to local disk, extracts text, and persists extracted metadata.",
)
async def upload_document(
    file: UploadFile = File(..., description="The document file to upload (PDF, DOCX, TXT, CSV)"),
    department: str = Form("General", description="Associated department or workspace"),
    owner: str = Form("System", description="Owner or creator name"),
    description: Optional[str] = Form(None, description="Optional document summary"),
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Accept multipart file upload, validate, store securely, and trigger text extraction."""
    if not file.filename or not file.filename.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must not be empty.",
        )

    # 1. Read binary content
    try:
        content_bytes = await file.read()
    except Exception as exc:
        logger.error(f"Error reading uploaded file '{file.filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read uploaded file payload: {exc}",
        )

    # 2. Validate file size, extension, and content signatures (magic bytes)
    try:
        file_ext, mime_type = storage_service.validate_file(
            filename=file.filename,
            content_bytes=content_bytes,
            declared_content_type=file.content_type,
        )
    except FileSizeExceededError as exc:
        logger.warning(f"File size limit exceeded for '{file.filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        )
    except InvalidFileTypeError as exc:
        logger.warning(f"Invalid file upload rejected for '{file.filename}': {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # 3. Generate document UUID and safely persist file
    doc_id = str(uuid.uuid4())
    sanitized_filename = storage_service.sanitize_filename(file.filename)

    try:
        abs_path, relative_storage_path = storage_service.save_file(
            document_id=doc_id,
            original_filename=file.filename,
            content_bytes=content_bytes,
        )
    except Exception as exc:
        logger.error(f"Failed to store file on disk for document {doc_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file to persistent storage.",
        )

    # 4. Create document database record
    try:
        doc = await document_service.create_document_from_upload(
            db=db,
            filename=sanitized_filename,
            original_filename=file.filename,
            file_type=file_ext,
            file_size=len(content_bytes),
            department=department,
            owner=owner,
            description=description,
            storage_path=relative_storage_path,
            mime_type=mime_type,
            doc_id=doc_id,
        )
    except Exception as exc:
        logger.error(f"Failed to record document metadata in DB: {exc}", exc_info=True)
        storage_service.delete_document_files(doc_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record document in database.",
        )

    # 5. Execute extraction and store content
    processed_doc = await document_service.process_document(db=db, document_id=doc.id)

    return DocumentResponse.model_validate(processed_doc)


@router.post(
    "/{document_id}/process",
    response_model=DocumentResponse,
    summary="Process or Reprocess Document",
    description="Trigger text extraction and metadata indexing for an already stored document.",
)
async def process_document_endpoint(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Reprocess an existing document."""
    doc = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    processed_doc = await document_service.process_document(db=db, document_id=document_id)
    return DocumentResponse.model_validate(processed_doc)


@router.get(
    "/{document_id}/download",
    summary="Download Original Document File",
    description="Retrieve the original uploaded document binary from safe storage with path traversal protection.",
)
async def download_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Serve the original uploaded document file."""
    doc = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    if not doc.storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No stored binary file available for document '{document_id}'.",
        )

    try:
        file_path = storage_service.get_document_file_path(
            document_id=doc.id,
            storage_path=doc.storage_path,
        )
    except StorageError as exc:
        logger.error(f"Storage lookup error for document {document_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored file is not available on disk.",
        )

    return FileResponse(
        path=str(file_path),
        filename=doc.original_filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


@router.get(
    "/{document_id}/content",
    response_model=DocumentContentResponse,
    summary="Get Extracted Text Content",
    description="Retrieve the extracted plain text, character count, and word count for a processed document.",
)
async def get_document_content_endpoint(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentContentResponse:
    """Fetch extracted text and token metrics for a document."""
    doc = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    content = await document_service.get_document_content(db=db, document_id=document_id)
    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extracted content not found for document '{document_id}'. "
                   f"Current extraction status is '{doc.extraction_status}'.",
        )

    return DocumentContentResponse.model_validate(content)


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunkListResponse,
    summary="Get Document Chunks",
    description="Retrieve paginated, structure-aware text chunks for a processed document with provenance and token counts.",
)
async def get_document_chunks_endpoint(
    document_id: str,
    skip: int = Query(0, ge=0, description="Number of chunks to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of chunks to return"),
    page_number: Optional[int] = Query(None, ge=1, description="Filter chunks by source page number"),
    db: AsyncSession = Depends(get_db),
) -> DocumentChunkListResponse:
    """Fetch paginated discrete chunks for a document."""
    doc = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    chunks, total = await document_service.get_document_chunks(
        db=db,
        document_id=document_id,
        skip=skip,
        limit=limit,
        page_number=page_number,
    )

    return DocumentChunkListResponse(
        total=total,
        document_id=document_id,
        skip=skip,
        limit=limit,
        chunks=[DocumentChunkResponse.model_validate(c) for c in chunks],
    )


@router.get(
    "/{document_id}/chunks/{chunk_index}",
    response_model=DocumentChunkResponse,
    summary="Get Document Chunk by Index",
    description="Retrieve a specific text chunk by its 0-based document sequence index.",
)
async def get_document_chunk_by_index_endpoint(
    document_id: str,
    chunk_index: int,
    db: AsyncSession = Depends(get_db),
) -> DocumentChunkResponse:
    """Fetch single chunk by sequence index."""
    doc = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    chunk = await document_service.get_document_chunk_by_index(
        db=db,
        document_id=document_id,
        chunk_index=chunk_index,
    )
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk with index {chunk_index} not found for document '{document_id}'.",
        )

    return DocumentChunkResponse.model_validate(chunk)


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Document Metadata (Legacy)",
    description="Register metadata for a new document without file payload.",
)
@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Create a new document metadata record."""
    document = await document_service.create_document(db=db, doc_in=doc_in)
    return DocumentResponse.model_validate(document)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List Document Metadata",
    description="Retrieve paginated document metadata records with optional filtering by department, file type, status, or search keywords.",
)
@router.get("/", response_model=DocumentListResponse, include_in_schema=False)
async def list_documents(
    department: Optional[str] = Query(None, description="Filter by department"),
    file_type: Optional[str] = Query(None, description="Filter by file type (e.g., pdf, docx, txt, csv)"),
    status: Optional[str] = Query(None, description="Filter by lifecycle status (uploaded, processing, processed, failed)"),
    search: Optional[str] = Query(None, description="Search keyword in filename, title, or description"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    db: AsyncSession = Depends(get_db),
) -> DocumentListResponse:
    """List document metadata records."""
    docs, total = await document_service.get_documents(
        db=db,
        department=department,
        file_type=file_type,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )
    return DocumentListResponse(
        total=total,
        documents=[DocumentResponse.model_validate(d) for d in docs],
    )


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get Document Metadata by ID",
    description="Retrieve metadata for a specific document by its unique UUID.",
)
async def get_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Fetch single document metadata record."""
    document = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    return DocumentResponse.model_validate(document)


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Update Document Metadata",
    description="Partially update an existing document metadata record.",
)
async def update_document(
    document_id: str,
    doc_update: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> DocumentResponse:
    """Update fields of an existing document metadata record."""
    document = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    updated_doc = await document_service.update_document(
        db=db, document=document, doc_update=doc_update
    )
    return DocumentResponse.model_validate(updated_doc)


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete Document",
    description="Delete a document record, its extracted text content, and disk storage files.",
)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete document metadata, content, and files."""
    document = await document_service.get_document_by_id(db=db, document_id=document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )
    await document_service.delete_document(db=db, document=document)
    return {"message": "Document deleted successfully", "id": document_id}


@router.post(
    "/{document_id}/embeddings",
    response_model=EmbeddingTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate or Refresh Document Chunk Embeddings",
    description="Embeds all chunks for a document using the configured embedding model and persists vectors in PostgreSQL.",
)
async def generate_document_embeddings(
    document_id: str,
    force: bool = Query(False, description="If True, re-embed even if chunk content has not changed"),
    db: AsyncSession = Depends(get_db),
) -> EmbeddingTaskResponse:
    """Generate dense vector embeddings for document chunks."""
    return await EmbeddingService.generate_document_embeddings(
        db=db,
        document_id=document_id,
        force=force,
    )


@router.get(
    "/{document_id}/embedding-status",
    response_model=DocumentEmbeddingStatusResponse,
    summary="Get Document Embedding Status",
    description="Check the current embedding status, total embedded chunks, model, and staleness for a document.",
)
async def get_document_embedding_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentEmbeddingStatusResponse:
    """Retrieve detailed embedding status for a document."""
    return await EmbeddingService.get_embedding_status(
        db=db,
        document_id=document_id,
    )



# ──────────────────────────────────────────────────────────────────────────
# Step 7 — Entity Extraction endpoints (appended to documents router)
# ──────────────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/entities/extract",
    response_model=EntityExtractionTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Entity Extraction for a Document",
    description="Extract named entities from all processed chunks of the specified document.",
)
async def extract_document_entities(
    document_id: str,
    force: bool = Query(False, description="Re-extract even if already processed"),
    db: AsyncSession = Depends(get_db),
) -> EntityExtractionTaskResponse:
    """Trigger entity extraction for a document's chunks."""
    try:
        stats = await EntityExtractionService.extract_document_entities(
            db=db, document_id=document_id, force=force
        )
        return EntityExtractionTaskResponse(
            document_id=document_id,
            status="completed",
            message=(
                f"Extracted {stats.entities_found} mentions, "
                f"{stats.unique_entities} unique entities from "
                f"{stats.processed_chunks}/{stats.total_chunks} chunks."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Entity extraction failed for document %s: %s", document_id, type(exc).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Entity extraction encountered an unexpected error",
        )


@router.get(
    "/{document_id}/entities/status",
    response_model=DocumentEntityStatusResponse,
    summary="Get Document Entity Extraction Status",
    description="Returns entity extraction state, mention count, and unique entity count.",
)
async def get_document_entity_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentEntityStatusResponse:
    """Retrieve entity extraction status for a document."""
    result = await EntityExtractionService.get_document_entity_status(
        db=db, document_id=document_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )
    return DocumentEntityStatusResponse(**result)


@router.get(
    "/{document_id}/entities",
    summary="List Document Entities",
    description=(
        "Return paginated entity mentions for a document with optional filters for "
        f"entity_type ({', '.join(ENTITY_TYPES_SORTED)}), search, and min_confidence."
    ),
)
async def list_document_entities(
    document_id: str,
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    search: Optional[str] = Query(None, description="Substring search on canonical name"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List entity mentions for a document with optional filters."""
    entities, total = await EntityExtractionService.list_document_entities(
        db=db,
        document_id=document_id,
        entity_type=entity_type,
        search=search,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "document_id": document_id,
        "entities": entities,
    }


# ──────────────────────────────────────────────────────────────────────────
# Step 8 — Relationship Extraction endpoints
# ──────────────────────────────────────────────────────────────────────────


@router.post(
    "/{document_id}/relationships/extract",
    response_model=RelationshipExtractionTaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger Relationship Extraction for a Document",
    description="Extract typed relationships between pre-extracted entities for all chunks of the specified document.",
)
async def extract_document_relationships(
    document_id: str,
    force: bool = Query(False, description="Re-extract even if already processed"),
    db: AsyncSession = Depends(get_db),
) -> RelationshipExtractionTaskResponse:
    """Trigger relationship extraction across pre-extracted entities in this document."""
    try:
        stats = await RelationshipExtractionService.extract_document_relationships(
            db=db, document_id=document_id, force=force
        )
        return RelationshipExtractionTaskResponse(
            document_id=document_id,
            status="completed",
            message=(
                f"Extracted {stats.relationships_created} relationships "
                f"({stats.unresolved} unresolved) from {stats.processed_chunks}/{stats.total_chunks} chunks."
            ),
            stats=stats,
        )
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    except Exception as exc:
        logger.error("Relationship extraction failed for document %s: %s", document_id, type(exc).__name__, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Relationship extraction encountered an unexpected error",
        )


@router.get(
    "/{document_id}/relationships/status",
    response_model=DocumentRelationshipStatusResponse,
    summary="Get Document Relationship Extraction Status",
    description="Returns relationship extraction state, total chunks, and relationship count.",
)
async def get_document_relationship_status(
    document_id: str,
    db: AsyncSession = Depends(get_db),
) -> DocumentRelationshipStatusResponse:
    """Retrieve relationship extraction status for a document."""
    result = await RelationshipExtractionService.get_document_relationship_status(
        db=db, document_id=document_id
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )
    return DocumentRelationshipStatusResponse(**result)


@router.get(
    "/{document_id}/relationships",
    response_model=RelationshipListResponse,
    summary="List Document Relationships",
    description="Return paginated entity relationships extracted for a document with optional filters.",
)
async def list_document_relationships(
    document_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    source_entity_id: Optional[str] = Query(None, description="Filter by source entity ID"),
    target_entity_id: Optional[str] = Query(None, description="Filter by target entity ID"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence threshold"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> RelationshipListResponse:
    """List entity relationships for a document with optional filters."""
    doc = await document_service.get_document_by_id(db, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found",
        )
    results, total = await RelationshipExtractionService.list_document_relationships(
        db=db,
        document_id=document_id,
        relationship_type=relationship_type,
        source_entity_id=source_entity_id,
        target_entity_id=target_entity_id,
        min_confidence=min_confidence,
        page=page,
        page_size=page_size,
    )
    return RelationshipListResponse(
        total=total,
        page=page,
        page_size=page_size,
        relationships=results,
    )
