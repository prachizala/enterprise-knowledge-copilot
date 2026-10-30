"""Graph synchronization service: syncing PostgreSQL documents, chunks, entities, and relationships into Neo4j."""

import logging
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.graph.client import Neo4jClient, get_neo4j_client
from app.graph.queries import (
    MERGE_CHUNK_QUERY,
    MERGE_DOCUMENT_QUERY,
    MERGE_ENTITY_QUERY,
    MERGE_MENTION_QUERY,
    build_merge_relationship_query,
    sanitize_relationship_type,
)
from app.graph.repository import GraphRepository
from app.graph.schemas import GraphSyncResponse
from app.models.document import Document, DocumentChunk
from app.models.entity import ChunkEntity, Entity
from app.models.relationship import EntityRelationship

logger = logging.getLogger(__name__)


class GraphSyncService:
    """Synchronizes structured enterprise entities and relationships from PostgreSQL into Neo4j."""

    def __init__(
        self,
        client: Optional[Neo4jClient] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        self._custom_client = client
        self._db = db

    @property
    def _client(self) -> Neo4jClient:
        return self._custom_client or get_neo4j_client()

    @property
    def _repository(self) -> GraphRepository:
        return GraphRepository(self._client)

    async def sync_all(
        self,
        db: Optional[AsyncSession] = None,
        force: bool = False,
    ) -> GraphSyncResponse:
        """Convenience method for full synchronization."""
        target_db = db or self._db
        if target_db is None:
            raise ValueError("AsyncSession (db) must be provided to sync_all")
        return await self.sync(db=target_db, document_id=None, force=force)

    async def sync_document(
        self,
        document_id: str,
        db: Optional[AsyncSession] = None,
        force: bool = False,
    ) -> GraphSyncResponse:
        """Convenience method for document-scoped synchronization."""
        target_db = db or self._db
        if target_db is None:
            raise ValueError("AsyncSession (db) must be provided to sync_document")
        return await self.sync(db=target_db, document_id=document_id, force=force)

    async def sync(
        self,
        db: AsyncSession,
        document_id: Optional[str] = None,
        force: bool = False,
    ) -> GraphSyncResponse:
        """Execute full or document-scoped synchronization from PostgreSQL into Neo4j.

        Args:
            db: Active async PostgreSQL session.
            document_id: Optional document UUID for targeted synchronization.
            force: If True, re-syncs records unconditionally.

        Returns:
            GraphSyncResponse with processing counts and latency.
        """
        start_time = time.perf_counter()
        resp = GraphSyncResponse()

        # Check connectivity
        if not self._client.is_connected:
            connected = await self._client.connect()
            if not connected:
                resp.errors = 1
                resp.message = "Failed to connect to Neo4j. Graph sync aborted."
                resp.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return resp

        # Ensure schema constraints and indexes exist before inserting
        await self._repository.init_schema()

        try:
            # ── 1. Sync Documents ─────────────────────────────────────────
            doc_stmt = select(Document)
            if document_id:
                doc_stmt = doc_stmt.where(Document.id == document_id)
            docs = (await db.execute(doc_stmt)).scalars().all()

            for doc in docs:
                await self._client.execute_query(
                    MERGE_DOCUMENT_QUERY,
                    {
                        "id": doc.id,
                        "filename": doc.filename,
                        "file_type": doc.file_type or "unknown",
                        "department": doc.department or "General",
                        "owner": doc.owner or "System",
                        "updated_at": doc.updated_at.isoformat() if doc.updated_at else "",
                    },
                )
                resp.documents_synced += 1

            # ── 2. Sync Document Chunks ───────────────────────────────────
            chunk_stmt = select(DocumentChunk)
            if document_id:
                chunk_stmt = chunk_stmt.where(DocumentChunk.document_id == document_id)
            chunks = (await db.execute(chunk_stmt)).scalars().all()

            for chunk in chunks:
                await self._client.execute_query(
                    MERGE_CHUNK_QUERY,
                    {
                        "id": chunk.id,
                        "document_id": chunk.document_id,
                        "chunk_index": chunk.chunk_index,
                        "char_count": chunk.char_count,
                        "token_count": chunk.token_count,
                        "section_header": chunk.section_header or "",
                        "page_number": chunk.page_number or 0,
                        "content_hash": chunk.content_hash or "",
                        "updated_at": chunk.updated_at.isoformat() if chunk.updated_at else "",
                    },
                )
                resp.chunks_synced += 1

            # ── 3. Sync Canonical Entities ────────────────────────────────
            if document_id:
                # Sync entities referenced in this document
                ent_stmt = (
                    select(Entity)
                    .join(ChunkEntity, Entity.id == ChunkEntity.entity_id)
                    .where(ChunkEntity.document_id == document_id)
                    .distinct()
                )
            else:
                ent_stmt = select(Entity)
            entities = (await db.execute(ent_stmt)).scalars().all()

            for ent in entities:
                await self._client.execute_query(
                    MERGE_ENTITY_QUERY,
                    {
                        "id": ent.id,
                        "entity_type": ent.entity_type,
                        "canonical_name": ent.canonical_name,
                        "display_name": ent.display_name,
                        "description": ent.description or "",
                        "updated_at": ent.updated_at.isoformat() if ent.updated_at else "",
                    },
                )
                resp.entities_synced += 1

            # ── 4. Sync Entity Mentions (Entity -> Chunk) ─────────────────
            mention_stmt = select(ChunkEntity)
            if document_id:
                mention_stmt = mention_stmt.where(ChunkEntity.document_id == document_id)
            mentions = (await db.execute(mention_stmt)).scalars().all()

            for m in mentions:
                await self._client.execute_query(
                    MERGE_MENTION_QUERY,
                    {
                        "mention_id": m.id,
                        "entity_id": m.entity_id,
                        "chunk_id": m.chunk_id,
                        "mention_text": m.mention_text,
                        "confidence": float(m.confidence),
                        "start_char": m.start_char or 0,
                        "end_char": m.end_char or 0,
                    },
                )
                resp.mentions_synced += 1

            # ── 5. Sync Entity Relationships ──────────────────────────────
            rel_stmt = select(EntityRelationship)
            if document_id:
                rel_stmt = rel_stmt.where(EntityRelationship.document_id == document_id)
            relationships = (await db.execute(rel_stmt)).scalars().all()

            for rel in relationships:
                safe_type = sanitize_relationship_type(rel.relationship_type)
                query = build_merge_relationship_query(safe_type)
                await self._client.execute_query(
                    query,
                    {
                        "relationship_id": rel.id,
                        "source_entity_id": rel.source_entity_id,
                        "target_entity_id": rel.target_entity_id,
                        "relationship_type": rel.relationship_type,
                        "confidence": float(rel.confidence),
                        "evidence_text": rel.evidence_text or "",
                        "document_id": rel.document_id,
                        "chunk_id": rel.chunk_id,
                        "source_start_char": rel.source_start_char or 0,
                        "source_end_char": rel.source_end_char or 0,
                        "target_start_char": rel.target_start_char or 0,
                        "target_end_char": rel.target_end_char or 0,
                        "provider": rel.provider or "",
                        "model": rel.model or "",
                        "created_at": rel.created_at.isoformat() if rel.created_at else "",
                        "updated_at": rel.updated_at.isoformat() if rel.updated_at else "",
                    },
                )
                resp.relationships_synced += 1

            resp.message = (
                f"Successfully synchronized {resp.entities_synced} entities, "
                f"{resp.relationships_synced} relationships, and {resp.chunks_synced} chunks to Neo4j."
            )

        except Exception as exc:
            logger.error("Error during Neo4j synchronization: %s", exc, exc_info=True)
            resp.errors += 1
            resp.message = f"Synchronization error: {str(exc)}"

        resp.duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return resp


graph_sync_service = GraphSyncService()
