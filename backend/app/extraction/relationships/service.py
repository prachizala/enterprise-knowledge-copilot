"""Relationship extraction service: orchestrates chunk extraction, validation, resolution, and persistence."""

import json
import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.extraction.relationships.base import RelationshipExtractionError
from app.extraction.relationships.normalization import normalize_relationship_type
from app.extraction.relationships.provider import get_relationship_extraction_provider
from app.extraction.relationships.schemas import (
    EntitySummary,
    ExtractedRelationship,
    RelationshipExtractionStats,
    RelationshipResponse,
)
from app.models.document import Document, DocumentChunk, generate_uuid_str, get_utc_now
from app.models.entity import ChunkEntity, Entity
from app.models.relationship import EntityRelationship

logger = logging.getLogger(__name__)


def _normalize_match_str(s: str) -> str:
    """Normalize string for fuzzy-safe entity matching."""
    s = unicodedata.normalize("NFKC", str(s)).strip().lower()
    return re.sub(r"\s+", " ", s).rstrip(".,;:")


class RelationshipExtractionService:
    """Service handling extraction, endpoint resolution, and queries for Entity Relationships."""

    @staticmethod
    async def extract_document_relationships(
        db: AsyncSession,
        document_id: str,
        force: bool = False,
    ) -> RelationshipExtractionStats:
        """Extract relationships across all chunks of *document_id* using pre-extracted entities.

        Enforces Step 8 dependency:
          Chunk -> Entity Extraction -> Relationship Extraction
        Raises ValueError if no entities have been extracted for this document.
        """
        # 1. Fetch document
        doc_result = await db.execute(select(Document).where(Document.id == document_id))
        document = doc_result.scalar_one_or_none()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        # 2. Dependency check: verify that entities exist for this document
        entity_count_res = await db.execute(
            select(func.count(ChunkEntity.id)).where(ChunkEntity.document_id == document_id)
        )
        total_chunk_entities = entity_count_res.scalar_one() or 0
        if total_chunk_entities == 0:
            raise ValueError(
                "No extracted entities are available for this document. "
                "Run entity extraction first."
            )

        provider = get_relationship_extraction_provider()
        provider_name = provider.provider_name
        model_name = provider.model_name

        min_confidence = settings.RELATIONSHIP_EXTRACTION_MIN_CONFIDENCE

        # 3. Mark document as processing
        document.relationship_extraction_status = "processing"
        await db.commit()

        # 4. Load all chunks for this document
        chunks_res = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        all_chunks: List[DocumentChunk] = list(chunks_res.scalars().all())

        stats = RelationshipExtractionStats(
            document_id=document_id,
            total_chunks=len(all_chunks),
        )

        if not all_chunks:
            document.relationship_extraction_status = "completed"
            await db.commit()
            return stats

        # 5. Check cached chunks (idempotency via content_hash, provider, model)
        processed_chunk_ids: set[str] = set()
        if not force:
            cached_res = await db.execute(
                select(EntityRelationship.chunk_id)
                .where(
                    EntityRelationship.document_id == document_id,
                    EntityRelationship.provider == provider_name,
                    EntityRelationship.model == model_name,
                )
                .distinct()
            )
            for row in cached_res.all():
                processed_chunk_ids.add(row[0])

        # 6. Process chunks
        for chunk in all_chunks:
            # Skip if already processed for this provider and model
            if not force and chunk.id in processed_chunk_ids:
                stats.skipped += 1
                continue

            # Load all ChunkEntity rows for this chunk joined with Entity
            chunk_entities_res = await db.execute(
                select(ChunkEntity, Entity)
                .join(Entity, ChunkEntity.entity_id == Entity.id)
                .where(ChunkEntity.chunk_id == chunk.id)
            )
            ce_pairs = chunk_entities_res.all()

            # Need at least 2 entities in the chunk to form relationships
            if len(ce_pairs) < 2:
                stats.processed_chunks += 1
                continue

            # Build entity payload and resolution lookup tables
            entities_payload: List[Dict[str, Any]] = []
            alias_to_entity: Dict[str, Entity] = {}
            name_to_entity: Dict[str, Entity] = {}
            mention_to_offsets: Dict[str, Tuple[Optional[int], Optional[int]]] = {}

            seen_entity_ids = set()
            for idx, (ce, ent) in enumerate(ce_pairs):
                alias_id = f"E{idx + 1}"
                alias_to_entity[alias_id.upper()] = ent
                name_to_entity[_normalize_match_str(ent.canonical_name)] = ent
                name_to_entity[_normalize_match_str(ent.display_name)] = ent
                name_to_entity[_normalize_match_str(ce.mention_text)] = ent

                if ce.mention_text:
                    mention_to_offsets[_normalize_match_str(ce.mention_text)] = (
                        ce.start_char,
                        ce.end_char,
                    )

                if ent.id not in seen_entity_ids:
                    seen_entity_ids.add(ent.id)
                    entities_payload.append({
                        "entity_id": ent.id,
                        "alias_id": alias_id,
                        "canonical_name": ent.canonical_name,
                        "display_name": ent.display_name,
                        "entity_type": ent.entity_type,
                        "mention_text": ce.mention_text,
                    })

            try:
                raw_relations = await provider.extract_relationships(
                    chunk_text=chunk.content,
                    entities=entities_payload,
                    metadata={
                        "chunk_id": chunk.id,
                        "document_id": document_id,
                        "section_header": chunk.section_header or "",
                    },
                )

                for raw in raw_relations:
                    stats.relationships_found += 1

                    # Source & Target identifier strings
                    src_raw = str(
                        raw.get("source_entity")
                        or raw.get("source_entity_text")
                        or raw.get("source")
                        or ""
                    ).strip()
                    tgt_raw = str(
                        raw.get("target_entity")
                        or raw.get("target_entity_text")
                        or raw.get("target")
                        or ""
                    ).strip()
                    raw_type = str(
                        raw.get("relationship_type")
                        or raw.get("type")
                        or ""
                    ).strip()
                    confidence = float(raw.get("confidence", 0.8))
                    evidence = raw.get("evidence_text")

                    # Confidence threshold check
                    if confidence < min_confidence:
                        continue

                    # Section 7: Entity Resolution
                    src_ent = (
                        alias_to_entity.get(src_raw.upper())
                        or name_to_entity.get(_normalize_match_str(src_raw))
                    )
                    tgt_ent = (
                        alias_to_entity.get(tgt_raw.upper())
                        or name_to_entity.get(_normalize_match_str(tgt_raw))
                    )

                    # If endpoint cannot be resolved confidently: DO NOT create relationship
                    if src_ent is None or tgt_ent is None:
                        stats.unresolved += 1
                        continue

                    # Reject self-referential relationships
                    if src_ent.id == tgt_ent.id:
                        stats.unresolved += 1
                        continue

                    # Section 11: Normalization
                    rel_type = normalize_relationship_type(raw_type)

                    # Offsets
                    src_offsets = mention_to_offsets.get(_normalize_match_str(src_raw), (None, None))
                    tgt_offsets = mention_to_offsets.get(_normalize_match_str(tgt_raw), (None, None))

                    # Sanitize evidence
                    clean_evidence = str(evidence).strip() if evidence else None
                    if clean_evidence and len(clean_evidence) > 1000:
                        clean_evidence = clean_evidence[:997] + "..."

                    # Section 13: Deduplication in the same chunk
                    existing_rel = await db.execute(
                        select(EntityRelationship).where(
                            EntityRelationship.source_entity_id == src_ent.id,
                            EntityRelationship.target_entity_id == tgt_ent.id,
                            EntityRelationship.relationship_type == rel_type,
                            EntityRelationship.chunk_id == chunk.id,
                        )
                    )
                    existing_row = existing_rel.scalar_one_or_none()

                    if existing_row is not None:
                        # Update confidence if newer extraction has higher confidence
                        if confidence > existing_row.confidence:
                            existing_row.confidence = confidence
                            if clean_evidence:
                                existing_row.evidence_text = clean_evidence
                    else:
                        rel_record = EntityRelationship(
                            id=generate_uuid_str(),
                            source_entity_id=src_ent.id,
                            target_entity_id=tgt_ent.id,
                            relationship_type=rel_type,
                            confidence=confidence,
                            evidence_text=clean_evidence,
                            chunk_id=chunk.id,
                            document_id=document_id,
                            source_start_char=src_offsets[0],
                            source_end_char=src_offsets[1],
                            target_start_char=tgt_offsets[0],
                            target_end_char=tgt_offsets[1],
                            content_hash=chunk.content_hash,
                            provider=provider_name,
                            model=model_name,
                        )
                        db.add(rel_record)
                        stats.relationships_created += 1

                await db.flush()
                stats.processed_chunks += 1

            except RelationshipExtractionError as exc:
                stats.failed_chunks += 1
                logger.warning(
                    "Relationship extraction failed for chunk %s: %s",
                    chunk.id,
                    type(exc).__name__,
                )
            except Exception as exc:
                stats.failed_chunks += 1
                logger.warning(
                    "Unexpected error in relationship extraction for chunk %s: %s",
                    chunk.id,
                    type(exc).__name__,
                )

        # 7. Update document relationship status and count
        total_rels_res = await db.execute(
            select(func.count(EntityRelationship.id)).where(
                EntityRelationship.document_id == document_id
            )
        )
        document.relationship_count = total_rels_res.scalar_one() or 0

        if stats.failed_chunks > 0 and stats.processed_chunks == 0:
            document.relationship_extraction_status = "failed"
        elif stats.failed_chunks > 0:
            document.relationship_extraction_status = "partial"
        else:
            document.relationship_extraction_status = "completed"

        await db.commit()
        logger.info(
            "Relationship extraction complete for %s: %d created, %d unresolved, %d failed chunks",
            document_id,
            stats.relationships_created,
            stats.unresolved,
            stats.failed_chunks,
        )
        return stats

    @staticmethod
    async def get_document_relationship_status(
        db: AsyncSession,
        document_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return relationship extraction status summary for a document."""
        doc_res = await db.execute(select(Document).where(Document.id == document_id))
        doc = doc_res.scalar_one_or_none()
        if doc is None:
            return None

        return {
            "document_id": document_id,
            "relationship_extraction_status": doc.relationship_extraction_status,
            "total_chunks": doc.total_chunks,
            "processed_chunks": doc.total_chunks,
            "relationships": doc.relationship_count,
            "failed_chunks": 0,
        }

    @staticmethod
    async def list_document_relationships(
        db: AsyncSession,
        document_id: str,
        relationship_type: Optional[str] = None,
        source_entity_id: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[RelationshipResponse], int]:
        """Return paginated relationships for a specific document with optional filtering."""
        stmt = (
            select(EntityRelationship)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(EntityRelationship.document_id == document_id)
        )
        count_stmt = (
            select(func.count())
            .select_from(EntityRelationship)
            .where(EntityRelationship.document_id == document_id)
        )

        if relationship_type:
            norm_type = normalize_relationship_type(relationship_type)
            stmt = stmt.where(EntityRelationship.relationship_type == norm_type)
            count_stmt = count_stmt.where(EntityRelationship.relationship_type == norm_type)
        if source_entity_id:
            stmt = stmt.where(EntityRelationship.source_entity_id == source_entity_id)
            count_stmt = count_stmt.where(EntityRelationship.source_entity_id == source_entity_id)
        if target_entity_id:
            stmt = stmt.where(EntityRelationship.target_entity_id == target_entity_id)
            count_stmt = count_stmt.where(EntityRelationship.target_entity_id == target_entity_id)
        if min_confidence > 0.0:
            stmt = stmt.where(EntityRelationship.confidence >= min_confidence)
            count_stmt = count_stmt.where(EntityRelationship.confidence >= min_confidence)

        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(EntityRelationship.confidence.desc()).offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        results = [RelationshipExtractionService._serialize_relationship(r) for r in rows]
        return results, total

    @staticmethod
    async def get_entity_relationships(
        db: AsyncSession,
        entity_id: str,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        """Return all outgoing and incoming relationships for a canonical entity."""
        # Outgoing
        out_stmt = (
            select(EntityRelationship)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(EntityRelationship.source_entity_id == entity_id)
            .order_by(EntityRelationship.confidence.desc())
        )
        out_count_stmt = (
            select(func.count())
            .select_from(EntityRelationship)
            .where(EntityRelationship.source_entity_id == entity_id)
        )
        total_out = (await db.execute(out_count_stmt)).scalar_one()
        out_rows = (await db.execute(out_stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()

        # Incoming
        in_stmt = (
            select(EntityRelationship)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(EntityRelationship.target_entity_id == entity_id)
            .order_by(EntityRelationship.confidence.desc())
        )
        in_count_stmt = (
            select(func.count())
            .select_from(EntityRelationship)
            .where(EntityRelationship.target_entity_id == entity_id)
        )
        total_in = (await db.execute(in_count_stmt)).scalar_one()
        in_rows = (await db.execute(in_stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()

        return {
            "entity_id": entity_id,
            "total_outgoing": total_out,
            "total_incoming": total_in,
            "outgoing": [RelationshipExtractionService._serialize_relationship(r) for r in out_rows],
            "incoming": [RelationshipExtractionService._serialize_relationship(r) for r in in_rows],
        }

    @staticmethod
    async def get_relationship_by_id(
        db: AsyncSession,
        relationship_id: str,
    ) -> Optional[RelationshipResponse]:
        """Retrieve relationship detail by UUID."""
        stmt = (
            select(EntityRelationship)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(EntityRelationship.id == relationship_id)
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            return None
        return RelationshipExtractionService._serialize_relationship(row)

    @staticmethod
    async def search_relationships(
        db: AsyncSession,
        q: str,
        relationship_type: Optional[str] = None,
        min_confidence: float = 0.0,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[RelationshipResponse], int]:
        """Search relationships by query across entity names, relationship type, or evidence."""
        pattern = f"%{q.lower()}%"

        # Create aliases for source and target entities
        from sqlalchemy.orm import aliased
        SourceEntity = aliased(Entity, name="src_ent")
        TargetEntity = aliased(Entity, name="tgt_ent")

        stmt = (
            select(EntityRelationship)
            .join(SourceEntity, EntityRelationship.source_entity_id == SourceEntity.id)
            .join(TargetEntity, EntityRelationship.target_entity_id == TargetEntity.id)
            .options(
                selectinload(EntityRelationship.source_entity),
                selectinload(EntityRelationship.target_entity),
            )
            .where(
                or_(
                    SourceEntity.canonical_name.ilike(pattern),
                    SourceEntity.display_name.ilike(pattern),
                    TargetEntity.canonical_name.ilike(pattern),
                    TargetEntity.display_name.ilike(pattern),
                    EntityRelationship.relationship_type.ilike(pattern),
                    EntityRelationship.evidence_text.ilike(pattern),
                )
            )
        )
        count_stmt = (
            select(func.count())
            .select_from(EntityRelationship)
            .join(SourceEntity, EntityRelationship.source_entity_id == SourceEntity.id)
            .join(TargetEntity, EntityRelationship.target_entity_id == TargetEntity.id)
            .where(
                or_(
                    SourceEntity.canonical_name.ilike(pattern),
                    SourceEntity.display_name.ilike(pattern),
                    TargetEntity.canonical_name.ilike(pattern),
                    TargetEntity.display_name.ilike(pattern),
                    EntityRelationship.relationship_type.ilike(pattern),
                    EntityRelationship.evidence_text.ilike(pattern),
                )
            )
        )

        if relationship_type:
            norm_type = normalize_relationship_type(relationship_type)
            stmt = stmt.where(EntityRelationship.relationship_type == norm_type)
            count_stmt = count_stmt.where(EntityRelationship.relationship_type == norm_type)

        if min_confidence > 0.0:
            stmt = stmt.where(EntityRelationship.confidence >= min_confidence)
            count_stmt = count_stmt.where(EntityRelationship.confidence >= min_confidence)

        total = (await db.execute(count_stmt)).scalar_one()

        offset = (page - 1) * page_size
        stmt = stmt.order_by(EntityRelationship.confidence.desc()).offset(offset).limit(page_size)
        rows = (await db.execute(stmt)).scalars().all()

        results = [RelationshipExtractionService._serialize_relationship(r) for r in rows]
        return results, total

    @staticmethod
    def _serialize_relationship(rel: EntityRelationship) -> RelationshipResponse:
        """Helper to serialize an EntityRelationship model into a RelationshipResponse."""
        return RelationshipResponse(
            id=rel.id,
            source_entity=EntitySummary(
                id=rel.source_entity.id,
                canonical_name=rel.source_entity.canonical_name,
                display_name=rel.source_entity.display_name,
                entity_type=rel.source_entity.entity_type,
            ),
            target_entity=EntitySummary(
                id=rel.target_entity.id,
                canonical_name=rel.target_entity.canonical_name,
                display_name=rel.target_entity.display_name,
                entity_type=rel.target_entity.entity_type,
            ),
            relationship_type=rel.relationship_type,
            confidence=rel.confidence,
            evidence_text=rel.evidence_text,
            chunk_id=rel.chunk_id,
            document_id=rel.document_id,
            source_start_char=rel.source_start_char,
            source_end_char=rel.source_end_char,
            target_start_char=rel.target_start_char,
            target_end_char=rel.target_end_char,
            provider=rel.provider,
            model=rel.model,
            created_at=rel.created_at.isoformat() if rel.created_at else None,
            updated_at=rel.updated_at.isoformat() if rel.updated_at else None,
        )


relationship_extraction_service = RelationshipExtractionService()
