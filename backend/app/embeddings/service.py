"""Service for generating, updating, and verifying chunk vector embeddings."""

from datetime import datetime, timezone
import hashlib
import logging
from typing import Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingError, EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.embeddings.schemas import (
    DocumentEmbeddingStatusResponse,
    EmbeddingTaskResponse,
    ReindexResponse,
)
from app.models.document import ChunkEmbedding, Document, DocumentChunk

logger = logging.getLogger(__name__)


def compute_content_hash(text: str) -> str:
    """Compute SHA-256 hash of text content for idempotency and staleness detection."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class EmbeddingService:
    """Coordinates embedding generation, persistence, and vector status tracking."""

    @staticmethod
    async def generate_document_embeddings(
        db: AsyncSession,
        document_id: str,
        force: bool = False,
        provider: Optional[EmbeddingProvider] = None,
    ) -> EmbeddingTaskResponse:
        """Generate dense vector embeddings for all chunks of a document.

        Args:
            db: Database session.
            document_id: Target document ID.
            force: If True, re-embeds even if content has not changed.
            provider: Optional explicit provider override.

        Returns:
            EmbeddingTaskResponse summarizing chunks embedded and status.
        """
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )

        # Retrieve chunks in index order
        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index.asc())
        )
        chunks_res = await db.execute(chunk_stmt)
        chunks = list(chunks_res.scalars().all())

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no chunks to embed. Ensure the document has been processed and chunked first.",
            )

        provider = provider or get_embedding_provider()
        model_name = provider.model_name
        dimensions = provider.dimensions

        # Update document status to processing
        document.embedding_status = "processing"
        await db.commit()
        await db.refresh(document)

        try:
            # Check existing embeddings for this document & model
            emb_stmt = select(ChunkEmbedding).where(
                ChunkEmbedding.document_id == document_id,
                ChunkEmbedding.model == model_name,
            )
            emb_res = await db.execute(emb_stmt)
            existing_embeddings: Dict[str, ChunkEmbedding] = {
                emb.chunk_id: emb for emb in emb_res.scalars().all()
            }

            chunks_to_embed: List[DocumentChunk] = []
            for chunk in chunks:
                current_hash = compute_content_hash(chunk.content)
                if chunk.content_hash != current_hash:
                    chunk.content_hash = current_hash

                if not force and chunk.id in existing_embeddings:
                    ext = existing_embeddings[chunk.id]
                    if ext.content_hash == current_hash and ext.dimensions == dimensions:
                        # Existing embedding is fresh and valid
                        continue

                chunks_to_embed.append(chunk)

            newly_embedded = 0
            if chunks_to_embed:
                logger.info(
                    "Generating %d embeddings for document '%s' with model '%s'",
                    len(chunks_to_embed),
                    document_id,
                    model_name,
                )
                texts = [c.content for c in chunks_to_embed]
                vectors = await provider.embed_texts(texts)

                for chunk, vector in zip(chunks_to_embed, vectors):
                    chunk_hash = chunk.content_hash or compute_content_hash(chunk.content)
                    if chunk.id in existing_embeddings:
                        existing = existing_embeddings[chunk.id]
                        existing.embedding = vector
                        existing.content_hash = chunk_hash
                        existing.dimensions = dimensions
                        existing.updated_at = datetime.now(timezone.utc)
                    else:
                        new_embedding = ChunkEmbedding(
                            chunk_id=chunk.id,
                            document_id=document.id,
                            embedding=vector,
                            model=model_name,
                            dimensions=dimensions,
                            content_hash=chunk_hash,
                        )
                        db.add(new_embedding)
                    newly_embedded += 1

                await db.flush()

            # Count total embeddings for this document
            total_count_stmt = select(func.count(ChunkEmbedding.id)).where(
                ChunkEmbedding.document_id == document_id,
                ChunkEmbedding.model == model_name,
            )
            total_embedded = await db.scalar(total_count_stmt) or 0

            document.embedding_status = "completed"
            document.embedded_chunks = total_embedded
            document.embedding_model = model_name
            await db.commit()

            message = (
                f"Successfully embedded {newly_embedded} new/updated chunks "
                f"({total_embedded}/{len(chunks)} total active embeddings)."
            )
            return EmbeddingTaskResponse(
                document_id=document_id,
                status="completed",
                total_chunks=len(chunks),
                embedded_chunks=total_embedded,
                model=model_name,
                message=message,
            )

        except Exception as exc:
            logger.exception("Error generating embeddings for document '%s': %s", document_id, exc)
            await db.rollback()
            # Mark document as failed
            try:
                document.embedding_status = "failed"
                await db.commit()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Embedding generation failed: {str(exc)}",
            )

    @staticmethod
    async def get_embedding_status(
        db: AsyncSession,
        document_id: str,
    ) -> DocumentEmbeddingStatusResponse:
        """Retrieve detailed embedding status for a document."""
        document = await db.get(Document, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID '{document_id}' not found.",
            )

        # Chunks and embeddings count
        chunk_count_stmt = select(func.count(DocumentChunk.id)).where(
            DocumentChunk.document_id == document_id
        )
        total_chunks = await db.scalar(chunk_count_stmt) or 0

        emb_count_stmt = select(func.count(ChunkEmbedding.id)).where(
            ChunkEmbedding.document_id == document_id
        )
        total_embeddings = await db.scalar(emb_count_stmt) or 0

        # Latest embedding timestamp
        last_date_stmt = select(func.max(ChunkEmbedding.updated_at)).where(
            ChunkEmbedding.document_id == document_id
        )
        last_embedded_at = await db.scalar(last_date_stmt)

        # Check staleness: are there chunks without embeddings or mismatched hash?
        is_up_to_date = (total_chunks > 0) and (total_chunks == total_embeddings)

        return DocumentEmbeddingStatusResponse(
            document_id=document_id,
            embedding_status=document.embedding_status,
            total_chunks=total_chunks,
            embedded_chunks=total_embeddings,
            embedding_model=document.embedding_model,
            is_up_to_date=is_up_to_date,
            last_embedded_at=last_embedded_at,
        )

    @staticmethod
    async def reindex_all_embeddings(
        db: AsyncSession,
        force: bool = False,
        document_ids: Optional[List[str]] = None,
        provider: Optional[EmbeddingProvider] = None,
    ) -> ReindexResponse:
        """Reindex embeddings across documents."""
        query = select(Document)
        if document_ids:
            query = query.where(Document.id.in_(document_ids))
        else:
            # Reindex processed documents
            query = query.where(Document.status == "processed")

        res = await db.execute(query)
        documents = list(res.scalars().all())

        provider = provider or get_embedding_provider()
        total_docs = len(documents)
        processed_docs = 0
        failed_docs = 0
        total_chunks_embedded = 0
        skipped_chunks = 0
        errors: List[str] = []

        for doc in documents:
            try:
                task = await EmbeddingService.generate_document_embeddings(
                    db=db,
                    document_id=doc.id,
                    force=force,
                    provider=provider,
                )
                processed_docs += 1
                total_chunks_embedded += task.embedded_chunks
            except Exception as e:
                failed_docs += 1
                errors.append(f"Doc {doc.id} ({doc.filename}): {str(e)}")

        return ReindexResponse(
            total_documents=total_docs,
            processed_documents=processed_docs,
            total_chunks_embedded=total_chunks_embedded,
            skipped_chunks=skipped_chunks,
            failed_documents=failed_docs,
            errors=errors,
        )

    # Alias for backward compatibility with older pipeline orchestrators
    embed_document_chunks = generate_document_embeddings
