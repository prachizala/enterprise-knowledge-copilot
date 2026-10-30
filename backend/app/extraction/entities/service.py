"""Entity extraction service: processes DocumentChunk records and persists entities.

Architecture:
  DocumentChunk → Provider.extract_entities() → validate + normalize → upsert Entity →
  insert ChunkEntity → update Document counts

Idempotency:
  Chunks whose (content_hash, provider, model) triple already exists in
  chunk_entities are skipped unless force=True is passed.

Resilience:
  Individual chunk failures are counted but do not abort the batch.
  Document status is set to "partial" if any chunks failed.
"""

import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.entities.base import EntityExtractionError
from app.extraction.entities.factory import get_entity_extraction_provider
from app.extraction.entities.registry import normalize_entity_type
from app.extraction.entities.schemas import ExtractedEntity, EntityExtractionStats
from app.models.document import Document, DocumentChunk, get_utc_now, generate_uuid_str
from app.models.entity import ChunkEntity, Entity

logger = logging.getLogger(__name__)


def _conservative_normalize(text: str) -> str:
    """Conservative canonical normalization for entity deduplication.

    Steps:
    1. Strip leading/trailing whitespace.
    2. Unicode NFKC normalization (e.g. ﬁ → fi).
    3. Collapse consecutive whitespace to a single space.
    4. Convert to lowercase.
    5. Strip trailing punctuation (period, comma, semicolon).

    Intentionally avoids aggressive fuzzy matching (no stemming, no phonetic)
    to prevent unintentional merges of distinct entities.
    """
    text = text.strip()
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    text = text.lower()
    text = text.rstrip(".,;:")
    return text


class EntityExtractionService:
    """Orchestrates entity extraction across all chunks of a document."""

    @staticmethod
    async def extract_document_entities(
        db: AsyncSession,
        document_id: str,
        force: bool = False,
    ) -> EntityExtractionStats:
        """Extract and persist entities for all chunks of *document_id*.

        Args:
            db: Async database session.
            document_id: Target document UUID.
            force: If True, re-extract even already-processed chunks.

        Returns:
            EntityExtractionStats with processing counters.

        Raises:
            ValueError: If the document does not exist.
        """
        # Fetch document
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        provider = get_entity_extraction_provider()
        provider_name = provider.provider_name
        model_name = provider.model_name

        from app.core.config import settings
        min_confidence = settings.ENTITY_EXTRACTION_MIN_CONFIDENCE
        batch_size = settings.ENTITY_EXTRACTION_BATCH_SIZE

        # Mark document as processing
        document.entity_extraction_status = "processing"
        await db.commit()

        # Load all chunks for this document
        chunks_result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        all_chunks: List[DocumentChunk] = list(chunks_result.scalars().all())

        stats = EntityExtractionStats(
            document_id=document_id,
            total_chunks=len(all_chunks),
        )

        if not all_chunks:
            logger.info("No chunks found for document %s — skipping entity extraction", document_id)
            document.entity_extraction_status = "completed"
            await db.commit()
            return stats

        # Build set of already-processed (content_hash, provider, model) for this document
        processed_keys: set[Tuple[Optional[str], str, str]] = set()
        if not force:
            existing_result = await db.execute(
                select(ChunkEntity.content_hash, ChunkEntity.provider, ChunkEntity.model)
                .where(ChunkEntity.document_id == document_id)
                .distinct()
            )
            for row in existing_result.all():
                processed_keys.add((row[0], row[1], row[2]))

        # Process in batches
        for batch_start in range(0, len(all_chunks), batch_size):
            batch = all_chunks[batch_start: batch_start + batch_size]

            for chunk in batch:
                chunk_key = (chunk.content_hash, provider_name, model_name)

                # Skip if already processed (unless force)
                if not force and chunk_key in processed_keys:
                    stats.skipped_chunks += 1
                    continue

                try:
                    raw_entities = await provider.extract_entities(
                        text=chunk.content,
                        metadata={
                            "chunk_id": chunk.id,
                            "document_id": document_id,
                            "chunk_index": chunk.chunk_index,
                            "section_header": chunk.section_header or "",
                            "page_number": chunk.page_number,
                        },
                    )

                    # Validate and normalize
                    validated: List[ExtractedEntity] = []
                    for raw in raw_entities:
                        try:
                            ent = ExtractedEntity.model_validate({
                                "text": raw.get("text", ""),
                                "type": raw.get("type", "OTHER"),
                                "normalized_name": raw.get("normalized_name") or _conservative_normalize(raw.get("text", "")),
                                "confidence": float(raw.get("confidence", 0.5)),
                                "start_char": raw.get("start_char"),
                                "end_char": raw.get("end_char"),
                            })
                            # Apply canonical normalization override
                            object.__setattr__(ent, "normalized_name", _conservative_normalize(ent.normalized_name or ent.text))
                            validated.append(ent)
                        except Exception as val_exc:
                            logger.debug("Entity validation failed for raw entity: %s", type(val_exc).__name__)
                            continue

                    # Persist validated entities
                    mention_count = await EntityExtractionService._persist_entities(
                        db=db,
                        chunk=chunk,
                        entities=validated,
                        document_id=document_id,
                        provider_name=provider_name,
                        model_name=model_name,
                        min_confidence=min_confidence,
                    )

                    stats.processed_chunks += 1
                    stats.entities_found += mention_count

                except EntityExtractionError as exc:
                    stats.failed_chunks += 1
                    logger.warning(
                        "Entity extraction failed for chunk %s of document %s: %s",
                        chunk.id,
                        document_id,
                        type(exc).__name__,
                    )
                except Exception as exc:
                    stats.failed_chunks += 1
                    logger.warning(
                        "Unexpected error extracting entities for chunk %s: %s",
                        chunk.id,
                        type(exc).__name__,
                    )

        # Compute unique entity count for this document
        unique_result = await db.execute(
            select(func.count(ChunkEntity.entity_id.distinct()))
            .where(ChunkEntity.document_id == document_id)
        )
        stats.unique_entities = unique_result.scalar_one() or 0

        # Update document record
        if stats.failed_chunks > 0 and stats.processed_chunks == 0:
            document.entity_extraction_status = "failed"
        elif stats.failed_chunks > 0:
            document.entity_extraction_status = "partial"
        else:
            document.entity_extraction_status = "completed"

        document.entity_mention_count = stats.entities_found
        document.unique_entity_count = stats.unique_entities

        await db.commit()
        logger.info(
            "Entity extraction complete for %s: %d mentions, %d unique entities, %d failed chunks",
            document_id,
            stats.entities_found,
            stats.unique_entities,
            stats.failed_chunks,
        )
        return stats

    @staticmethod
    async def _persist_entities(
        db: AsyncSession,
        chunk: DocumentChunk,
        entities: List[ExtractedEntity],
        document_id: str,
        provider_name: str,
        model_name: str,
        min_confidence: float,
    ) -> int:
        """Upsert canonical Entity rows and insert ChunkEntity mentions.

        Returns the number of mentions persisted (including low-confidence ones
        which are stored but flagged via their confidence value).
        """
        persisted = 0

        for ent in entities:
            # Attempt upsert of canonical Entity using unique constraint
            canonical_name = ent.normalized_name
            entity_type = normalize_entity_type(ent.type)

            # Try to find existing entity
            existing_result = await db.execute(
                select(Entity).where(
                    Entity.entity_type == entity_type,
                    Entity.canonical_name == canonical_name,
                )
            )
            entity_row = existing_result.scalar_one_or_none()

            if entity_row is None:
                entity_row = Entity(
                    id=generate_uuid_str(),
                    entity_type=entity_type,
                    canonical_name=canonical_name,
                    display_name=ent.text,
                    mention_count=0,
                    document_count=0,
                )
                db.add(entity_row)
                await db.flush()  # get the ID

            # Create the mention record
            mention = ChunkEntity(
                id=generate_uuid_str(),
                chunk_id=chunk.id,
                entity_id=entity_row.id,
                document_id=document_id,
                mention_text=ent.text,
                confidence=ent.confidence,
                start_char=ent.start_char,
                end_char=ent.end_char,
                content_hash=chunk.content_hash,
                provider=provider_name,
                model=model_name,
                section_header=chunk.section_header,
                page_number=chunk.page_number,
            )
            db.add(mention)
            entity_row.mention_count += 1
            persisted += 1

        await db.flush()
        return persisted

    @staticmethod
    async def get_document_entity_status(
        db: AsyncSession,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return entity extraction status dict for a document."""
        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if doc is None:
            return None
        return {
            "document_id": document_id,
            "entity_extraction_status": doc.entity_extraction_status,
            "entity_mention_count": doc.entity_mention_count,
            "unique_entity_count": doc.unique_entity_count,
            "total_chunks": doc.total_chunks,
        }

    @staticmethod
    async def list_document_entities(
        db: AsyncSession,
        document_id: str,
        entity_type: Optional[str] = None,
        search: Optional[str] = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Return paginated entity mentions for a document with optional filters.

        Returns:
            (list of mention dicts, total_count)
        """
        from sqlalchemy.orm import aliased

        stmt = (
            select(ChunkEntity, Entity)
            .join(Entity, ChunkEntity.entity_id == Entity.id)
            .where(ChunkEntity.document_id == document_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(ChunkEntity)
            .join(Entity, ChunkEntity.entity_id == Entity.id)
            .where(ChunkEntity.document_id == document_id)
        )

        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type.upper())
            count_stmt = count_stmt.where(Entity.entity_type == entity_type.upper())
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(Entity.canonical_name.ilike(pattern))
            count_stmt = count_stmt.where(Entity.canonical_name.ilike(pattern))
        if min_confidence > 0:
            stmt = stmt.where(ChunkEntity.confidence >= min_confidence)
            count_stmt = count_stmt.where(ChunkEntity.confidence >= min_confidence)

        total_result = await db.execute(count_stmt)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        rows = await db.execute(stmt)

        results = []
        for chunk_entity, entity in rows.all():
            results.append({
                "id": chunk_entity.id,
                "chunk_id": chunk_entity.chunk_id,
                "entity_id": chunk_entity.entity_id,
                "document_id": chunk_entity.document_id,
                "mention_text": chunk_entity.mention_text,
                "confidence": chunk_entity.confidence,
                "entity_type": entity.entity_type,
                "canonical_name": entity.canonical_name,
                "section_header": chunk_entity.section_header,
                "page_number": chunk_entity.page_number,
            })
        return results, total

    @staticmethod
    async def get_entity_by_id(
        db: AsyncSession,
        entity_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return a canonical entity by its UUID with mention provenance."""
        result = await db.execute(
            select(Entity).where(Entity.id == entity_id)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return {
            "id": entity.id,
            "entity_type": entity.entity_type,
            "canonical_name": entity.canonical_name,
            "display_name": entity.display_name,
            "description": entity.description,
            "mention_count": entity.mention_count,
            "document_count": entity.document_count,
            "created_at": entity.created_at.isoformat() if entity.created_at else None,
            "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
        }

    @staticmethod
    async def search_entities(
        db: AsyncSession,
        q: str,
        entity_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search canonical entities by name substring."""
        pattern = f"%{q.lower()}%"
        stmt = select(Entity).where(Entity.canonical_name.ilike(pattern))
        count_stmt = (
            select(func.count())
            .select_from(Entity)
            .where(Entity.canonical_name.ilike(pattern))
        )

        if entity_type:
            stmt = stmt.where(Entity.entity_type == entity_type.upper())
            count_stmt = count_stmt.where(Entity.entity_type == entity_type.upper())

        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(Entity.mention_count.desc()).offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        results = [
            {
                "id": e.id,
                "entity_type": e.entity_type,
                "canonical_name": e.canonical_name,
                "display_name": e.display_name,
                "description": e.description,
                "mention_count": e.mention_count,
                "document_count": e.document_count,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in rows
        ]
        return results, total


entity_extraction_service = EntityExtractionService()
