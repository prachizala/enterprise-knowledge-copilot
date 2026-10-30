"""Document metadata and processing service implementing async database operations."""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy import asc, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.extraction.base import ExtractionError
from app.extraction.service import extraction_service
from app.ingestion.chunker import StructureAwareChunker
from app.models.document import (
    Document,
    DocumentChunk,
    DocumentContent,
    generate_uuid_str,
    get_utc_now,
)
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.services.storage_service import storage_service

logger = logging.getLogger(__name__)


class DocumentService:
    """Service handling CRUD operations and processing pipelines for Enterprise Documents."""

    @staticmethod
    async def create_document(
        db: AsyncSession,
        doc_in: DocumentCreate,
    ) -> Document:
        """Create a new document metadata record (Step 3 compatibility)."""
        doc = Document(
            filename=doc_in.filename,
            original_filename=doc_in.original_filename,
            file_type=doc_in.file_type.lower(),
            file_size=doc_in.file_size,
            department=doc_in.department,
            owner=doc_in.owner,
            description=doc_in.description,
            version=doc_in.version,
            status="uploaded",
            extraction_status="pending",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def create_document_from_upload(
        db: AsyncSession,
        filename: str,
        original_filename: str,
        file_type: str,
        file_size: int,
        department: str,
        owner: str,
        description: Optional[str],
        storage_path: str,
        mime_type: str,
        doc_id: Optional[str] = None,
    ) -> Document:
        """Create document database entry initialized with storage path and pending extraction."""
        doc_kwargs = {
            "filename": filename,
            "original_filename": original_filename,
            "file_type": file_type.lower(),
            "file_size": file_size,
            "department": department,
            "owner": owner,
            "description": description,
            "version": "1.0",
            "status": "uploaded",
            "storage_path": storage_path,
            "mime_type": mime_type,
            "extraction_status": "pending",
            "extracted_text_length": 0,
        }
        if doc_id:
            doc_kwargs["id"] = doc_id
        doc = Document(**doc_kwargs)
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def get_document_by_id(
        db: AsyncSession,
        document_id: str,
    ) -> Optional[Document]:
        """Fetch a document by its primary key ID."""
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.content))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_documents(
        db: AsyncSession,
        department: Optional[str] = None,
        file_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Document], int]:
        """List documents with optional filtering, search, and pagination."""
        stmt = select(Document)
        count_stmt = select(func.count()).select_from(Document)

        filters = []
        if department and department.strip() and department.lower() != "all":
            filters.append(Document.department.ilike(department.strip()))

        if file_type and file_type.strip() and file_type.lower() != "all":
            filters.append(Document.file_type.ilike(file_type.strip()))

        if status and status.strip() and status.lower() != "all":
            filters.append(Document.status.ilike(status.strip()))

        if search and search.strip():
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(
                    Document.filename.ilike(pattern),
                    Document.original_filename.ilike(pattern),
                    Document.owner.ilike(pattern),
                    Document.department.ilike(pattern),
                    Document.description.ilike(pattern),
                )
            )

        if filters:
            stmt = stmt.where(*filters)
            count_stmt = count_stmt.where(*filters)

        # Get total count
        count_res = await db.execute(count_stmt)
        total = count_res.scalar_one()

        # Query paginated rows
        stmt = stmt.order_by(desc(Document.created_at)).offset(skip).limit(limit)
        res = await db.execute(stmt)
        docs = list(res.scalars().all())

        return docs, total

    @staticmethod
    async def update_document(
        db: AsyncSession,
        document: Document,
        doc_update: DocumentUpdate,
    ) -> Document:
        """Update fields of an existing document record."""
        update_data = doc_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(document, key) and value is not None:
                if key == "file_type" and isinstance(value, str):
                    value = value.lower()
                setattr(document, key, value)

        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def delete_document(
        db: AsyncSession,
        document: Document,
    ) -> None:
        """Delete a document record from the database and remove local storage files."""
        doc_id = document.id
        await db.delete(document)
        await db.commit()

        # Clean up storage directory
        try:
            storage_service.delete_document_files(doc_id)
        except Exception as exc:
            logger.warning(f"Storage cleanup notice for {doc_id}: {exc}")

    @staticmethod
    async def process_document(
        db: AsyncSession,
        document_id: str,
    ) -> Document:
        """Execute text extraction on document storage file and persist DocumentContent.

        Lifecycle:
            uploaded -> processing -> processed (or failed)

        Structured for simple sync execution or asynchronous background tasks.
        """
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.content))
        )
        result = await db.execute(stmt)
        document = result.scalar_one_or_none()

        if not document:
            raise ValueError(f"Document with ID '{document_id}' not found.")

        # 1. Transition state to 'processing'
        document.status = "processing"
        document.extraction_status = "processing"
        document.processing_error = None
        await db.commit()
        await db.refresh(document)

        start_time = time.perf_counter()
        logger.info(f"Starting text extraction for document {document.id} ({document.filename})")

        try:
            # 2. Resolve safe disk file path
            file_path = storage_service.get_document_file_path(
                document_id=document.id,
                storage_path=document.storage_path,
            )

            # 3. Perform text extraction using format extractor
            extracted = extraction_service.extract(
                file_path=file_path,
                file_type=document.file_type,
            )

            duration = time.perf_counter() - start_time
            logger.info(
                f"Extraction completed for {document.id} in {duration:.2f}s "
                f"({extracted.character_count} chars, {extracted.word_count} words)"
            )

            # 4. Upsert DocumentContent
            if document.content:
                # Update existing content
                document.content.text = extracted.text
                document.content.character_count = extracted.character_count
                document.content.word_count = extracted.word_count
                document.content.page_count = extracted.page_count
                document.content.updated_at = get_utc_now()
            else:
                # Create new content
                content = DocumentContent(
                    document_id=document.id,
                    text=extracted.text,
                    character_count=extracted.character_count,
                    word_count=extracted.word_count,
                    page_count=extracted.page_count,
                )
                db.add(content)

            # 5. Structure-aware Document Chunking
            chunker = StructureAwareChunker(chunk_size=600, chunk_overlap=100)
            chunks = chunker.chunk_text(
                text=extracted.text,
                file_type=document.file_type,
                document_metadata={
                    "document_id": document.id,
                    "filename": document.filename,
                    "department": document.department,
                    "owner": document.owner,
                    "page_count": extracted.page_count,
                },
            )

            # 6. Purge existing chunks if reprocessing
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )

            # 7. Persist newly generated discrete chunks
            chunk_models = [
                DocumentChunk(
                    id=generate_uuid_str(),
                    document_id=document.id,
                    chunk_index=ch.index,
                    content=ch.content,
                    char_count=ch.char_count,
                    token_count=ch.token_count,
                    page_number=ch.page_number,
                    section_header=ch.section_header,
                    chunk_metadata=json.dumps(ch.metadata) if ch.metadata else None,
                    content_hash=hashlib.sha256(ch.content.encode("utf-8")).hexdigest(),
                )
                for ch in chunks
            ]
            if chunk_models:
                db.add_all(chunk_models)

            # 8. Transition to processed
            document.status = "processed"
            document.extraction_status = "completed"
            document.extracted_text_length = extracted.character_count
            document.total_chunks = len(chunks)
            document.embedding_status = "pending"
            document.processing_error = None
            document.processed_at = get_utc_now()

            await db.commit()
            await db.refresh(document)
            logger.info(
                f"Successfully indexed {len(chunks)} chunks for document {document.id} ({document.filename})"
            )

            # 9. Trigger embedding generation if provider is available
            try:
                from app.embeddings.service import EmbeddingService
                await EmbeddingService.generate_document_embeddings(db=db, document_id=document.id)
                await db.refresh(document)
            except Exception as emb_exc:
                logger.warning(
                    "Automatic embedding generation skipped or deferred for document %s: %s",
                    document.id,
                    emb_exc,
                )

            # 10. Trigger entity extraction if provider is configured (non-blocking)
            try:
                from app.extraction.entities.service import EntityExtractionService
                await EntityExtractionService.extract_document_entities(
                    db=db, document_id=document.id
                )
                await db.refresh(document)
            except Exception as ent_exc:
                logger.warning(
                    "Automatic entity extraction skipped or deferred for document %s: %s",
                    document.id,
                    ent_exc,
                )

            # 11. Trigger relationship extraction if explicitly configured (non-blocking)
            try:
                from app.core.config import settings as app_settings
                if app_settings.RELATIONSHIP_EXTRACTION_PROVIDER:
                    from app.extraction.relationships.service import RelationshipExtractionService
                    await RelationshipExtractionService.extract_document_relationships(
                        db=db, document_id=document.id
                    )
                    await db.refresh(document)
            except Exception as rel_exc:
                logger.warning(
                    "Automatic relationship extraction skipped or deferred for document %s: %s",
                    document.id,
                    rel_exc,
                )

            return document

        except Exception as exc:
            duration = time.perf_counter() - start_time
            logger.error(f"Extraction failed for document {document.id} after {duration:.2f}s: {exc}", exc_info=True)

            # Safe error summary without exposing raw stack traces
            safe_error_msg = str(exc)
            if len(safe_error_msg) > 300:
                safe_error_msg = safe_error_msg[:297] + "..."

            document.status = "failed"
            document.extraction_status = "failed"
            document.processing_error = safe_error_msg
            document.processed_at = get_utc_now()

            await db.commit()
            await db.refresh(document)
            return document

    @staticmethod
    async def get_document_content(
        db: AsyncSession,
        document_id: str,
    ) -> Optional[DocumentContent]:
        """Fetch extracted DocumentContent for a document."""
        stmt = select(DocumentContent).where(DocumentContent.document_id == document_id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_document_chunks(
        db: AsyncSession,
        document_id: str,
        skip: int = 0,
        limit: int = 50,
        page_number: Optional[int] = None,
    ) -> Tuple[List[DocumentChunk], int]:
        """Retrieve paginated chunks for a document ordered by chunk_index ascending."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
        )

        if page_number is not None:
            stmt = stmt.where(DocumentChunk.page_number == page_number)
            count_stmt = count_stmt.where(DocumentChunk.page_number == page_number)

        count_res = await db.execute(count_stmt)
        total = count_res.scalar_one()

        stmt = stmt.order_by(asc(DocumentChunk.chunk_index)).offset(skip).limit(limit)
        res = await db.execute(stmt)
        chunks = list(res.scalars().all())

        return chunks, total

    @staticmethod
    async def get_document_chunk_by_index(
        db: AsyncSession,
        document_id: str,
        chunk_index: int,
    ) -> Optional[DocumentChunk]:
        """Retrieve a specific chunk by its 0-based document sequence index."""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.chunk_index == chunk_index,
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def get_document_chunk_by_id(
        db: AsyncSession,
        document_id: str,
        chunk_id: str,
    ) -> Optional[DocumentChunk]:
        """Retrieve a specific chunk by its UUID primary key."""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.id == chunk_id,
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


document_service = DocumentService()
