"""Semantic vector search service executing cosine similarity queries with document provenance."""

import logging
import math
import time
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.models.document import ChunkEmbedding, Document, DocumentChunk
from app.retrieval.schemas import (
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResultItem,
)

logger = logging.getLogger(__name__)


def _parse_vector(raw: object) -> List[float]:
    """Safely convert database vector output to a Python list of floats."""
    if hasattr(raw, "tolist"):
        return raw.tolist()  # type: ignore
    if isinstance(raw, (list, tuple)):
        return [float(x) for x in raw]
    if isinstance(raw, str):
        cleaned = raw.strip("[]() ")
        return [float(x.strip()) for x in cleaned.split(",") if x.strip()]
    return list(raw)  # type: ignore


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute cosine similarity between two float vectors, clamped to [0.0, 1.0]."""
    if len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    val = dot / (norm_a * norm_b)
    # Clamp cosine similarity for normalized semantic presentation
    return max(0.0, min(1.0, float(val)))


class VectorSearchService:
    """Performs semantic similarity searches over stored chunk embeddings."""

    @staticmethod
    async def search(
        db: AsyncSession,
        request: VectorSearchRequest,
        provider: Optional[EmbeddingProvider] = None,
    ) -> VectorSearchResponse:
        """Embed the search query and retrieve the top-k most semantically similar chunks.

        Supports metadata filtering by document_id, department, and file_type.
        Includes complete document provenance and chunk details in results.
        """
        start_time = time.perf_counter()
        provider = provider or get_embedding_provider()
        model_name = provider.model_name

        # 1. Embed user query string
        query_vector = await provider.embed_query(request.query)

        # 2. Inspect active database dialect
        dialect_name = db.bind.dialect.name if db.bind else "postgresql"

        results: List[VectorSearchResultItem] = []

        if dialect_name == "postgresql":
            # PostgreSQL + pgvector native HNSW cosine distance execution
            distance_expr = ChunkEmbedding.embedding.cosine_distance(query_vector)

            stmt = (
                select(
                    ChunkEmbedding,
                    DocumentChunk,
                    Document,
                    distance_expr.label("distance"),
                )
                .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .join(Document, ChunkEmbedding.document_id == Document.id)
                .where(ChunkEmbedding.model == model_name)
            )

            # Apply metadata filters
            if request.document_id:
                stmt = stmt.where(ChunkEmbedding.document_id == request.document_id)
            if request.department:
                stmt = stmt.where(Document.department == request.department)
            if request.file_type:
                stmt = stmt.where(Document.file_type == request.file_type.lower().strip("."))

            # Apply similarity threshold via distance condition (distance <= 1.0 - threshold)
            if request.similarity_threshold > 0.0:
                max_dist = 1.0 - request.similarity_threshold
                stmt = stmt.where(distance_expr <= max_dist)

            # Order by smallest cosine distance first, tie-breaking on chunk_index
            stmt = stmt.order_by(distance_expr.asc(), DocumentChunk.chunk_index.asc()).limit(request.top_k)

            exec_res = await db.execute(stmt)
            rows = exec_res.all()

            for emb, chunk, doc, dist in rows:
                dist_val = float(dist)
                sim_score = max(0.0, min(1.0, 1.0 - dist_val))
                results.append(
                    VectorSearchResultItem(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        document_filename=doc.filename,
                        document_original_filename=doc.original_filename,
                        department=doc.department,
                        owner=doc.owner,
                        file_type=doc.file_type,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        char_count=chunk.char_count,
                        token_count=chunk.token_count,
                        page_number=chunk.page_number,
                        section_header=chunk.section_header,
                        similarity_score=round(sim_score, 4),
                        distance=round(dist_val, 4),
                        model=model_name,
                    )
                )

        else:
            # SQLite in-memory fallback for unit testing without PostgreSQL container
            stmt = (
                select(ChunkEmbedding, DocumentChunk, Document)
                .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .join(Document, ChunkEmbedding.document_id == Document.id)
                .where(ChunkEmbedding.model == model_name)
            )

            if request.document_id:
                stmt = stmt.where(ChunkEmbedding.document_id == request.document_id)
            if request.department:
                stmt = stmt.where(Document.department == request.department)
            if request.file_type:
                stmt = stmt.where(Document.file_type == request.file_type.lower().strip("."))

            exec_res = await db.execute(stmt)
            rows = exec_res.all()

            scored_candidates = []
            for emb, chunk, doc in rows:
                emb_vec = _parse_vector(emb.embedding)
                sim = _cosine_similarity(query_vector, emb_vec)
                dist = max(0.0, 1.0 - sim)

                if sim >= request.similarity_threshold:
                    scored_candidates.append((sim, dist, emb, chunk, doc))

            # Sort descending by similarity, ascending by chunk_index
            scored_candidates.sort(key=lambda x: (-x[0], x[3].chunk_index))
            top_candidates = scored_candidates[: request.top_k]

            for sim, dist, emb, chunk, doc in top_candidates:
                results.append(
                    VectorSearchResultItem(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        document_filename=doc.filename,
                        document_original_filename=doc.original_filename,
                        department=doc.department,
                        owner=doc.owner,
                        file_type=doc.file_type,
                        chunk_index=chunk.chunk_index,
                        content=chunk.content,
                        char_count=chunk.char_count,
                        token_count=chunk.token_count,
                        page_number=chunk.page_number,
                        section_header=chunk.section_header,
                        similarity_score=round(sim, 4),
                        distance=round(dist, 4),
                        model=model_name,
                    )
                )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        return VectorSearchResponse(
            query=request.query,
            total_results=len(results),
            top_k=request.top_k,
            results=results,
            search_time_ms=round(elapsed_ms, 2),
            model=model_name,
        )

    @staticmethod
    async def search_candidates(
        db: AsyncSession,
        query: str,
        user: Optional[object] = None,
        top_k: int = 10,
        min_similarity: float = 0.25,
        department: Optional[str] = None,
        document_id: Optional[str] = None,
        provider: Optional[EmbeddingProvider] = None,
    ) -> List["VectorCandidate"]:
        """Retrieve VectorCandidate items enforcing document RBAC access control and deduplication."""
        from app.auth.dependencies import build_accessible_documents_filter
        from app.retrieval.schemas import VectorCandidate

        provider = provider or get_embedding_provider()
        model_name = provider.model_name
        query_vector = await provider.embed_query(query)

        dialect_name = db.bind.dialect.name if db.bind else "postgresql"
        candidates: List[VectorCandidate] = []
        seen_hashes = set()

        if dialect_name == "postgresql":
            distance_expr = ChunkEmbedding.embedding.cosine_distance(query_vector)
            stmt = (
                select(
                    ChunkEmbedding,
                    DocumentChunk,
                    Document,
                    distance_expr.label("distance"),
                )
                .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .join(Document, ChunkEmbedding.document_id == Document.id)
                .where(ChunkEmbedding.model == model_name)
            )

            # Enforce document-level RBAC (Phase 20)
            if user is not None:
                rbac_filter = build_accessible_documents_filter(user)
                if rbac_filter is not None:
                    stmt = stmt.where(rbac_filter)

            if document_id:
                stmt = stmt.where(ChunkEmbedding.document_id == document_id)
            if department:
                stmt = stmt.where(Document.department.ilike(department))

            if min_similarity > 0.0:
                stmt = stmt.where(distance_expr <= (1.0 - min_similarity))

            stmt = stmt.order_by(distance_expr.asc(), DocumentChunk.chunk_index.asc()).limit(top_k * 2)
            rows = (await db.execute(stmt)).all()

            for emb, chunk, doc, dist in rows:
                sim_score = max(0.0, min(1.0, 1.0 - float(dist)))
                if sim_score < min_similarity:
                    continue

                # Content-hash deduplication
                content_key = chunk.content.strip()
                if content_key in seen_hashes:
                    continue
                seen_hashes.add(content_key)

                candidates.append(
                    VectorCandidate(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        document_title=doc.original_filename or doc.filename,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_title=chunk.section_header,
                        content=chunk.content,
                        similarity_score=round(sim_score, 4),
                        department=doc.department,
                        content_hash=getattr(doc, "content_hash", None),
                    )
                )
                if len(candidates) >= top_k:
                    break

        else:
            # SQLite fallback for testing
            stmt = (
                select(ChunkEmbedding, DocumentChunk, Document)
                .join(DocumentChunk, ChunkEmbedding.chunk_id == DocumentChunk.id)
                .join(Document, ChunkEmbedding.document_id == Document.id)
                .where(ChunkEmbedding.model == model_name)
            )

            if user is not None:
                rbac_filter = build_accessible_documents_filter(user)
                if rbac_filter is not None:
                    stmt = stmt.where(rbac_filter)

            if document_id:
                stmt = stmt.where(ChunkEmbedding.document_id == document_id)
            if department:
                stmt = stmt.where(Document.department.ilike(department))

            rows = (await db.execute(stmt)).all()
            scored = []
            for emb, chunk, doc in rows:
                emb_vec = _parse_vector(emb.embedding)
                sim = _cosine_similarity(query_vector, emb_vec)
                if sim >= min_similarity:
                    scored.append((sim, emb, chunk, doc))

            scored.sort(key=lambda x: (-x[0], x[2].chunk_index))
            for sim, emb, chunk, doc in scored:
                content_key = chunk.content.strip()
                if content_key in seen_hashes:
                    continue
                seen_hashes.add(content_key)

                candidates.append(
                    VectorCandidate(
                        chunk_id=chunk.id,
                        document_id=doc.id,
                        document_title=doc.original_filename or doc.filename,
                        chunk_index=chunk.chunk_index,
                        page_number=chunk.page_number,
                        section_title=chunk.section_header,
                        content=chunk.content,
                        similarity_score=round(sim, 4),
                        department=doc.department,
                        content_hash=getattr(doc, "content_hash", None),
                    )
                )
                if len(candidates) >= top_k:
                    break

        return candidates
