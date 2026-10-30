"""Candidate Fusion: combines dense vector candidates, sparse BM25 candidates, and graph paths."""

import logging
from typing import Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.retrieval.schemas import (
    FusedCandidate,
    GraphCandidate,
    GraphPath,
    SparseCandidate,
    VectorCandidate,
)

logger = logging.getLogger(__name__)


class CandidateFusion:
    """Fuses heterogeneous retrieval candidates into a unified scored candidate pool (Tri-Hybrid RRF)."""

    @staticmethod
    async def fuse(
        db: AsyncSession,
        vector_candidates: List[VectorCandidate],
        graph_candidates: List[GraphCandidate],
        graph_paths: List[GraphPath],
        sparse_candidates: Optional[List[SparseCandidate]] = None,
        vector_weight: float = 0.40,
        sparse_weight: float = 0.30,
        graph_weight: float = 0.30,
        rrf_k: int = 60,
    ) -> List[FusedCandidate]:
        """Combine dense vector, sparse BM25, and knowledge graph evidence using Tri-Hybrid Reciprocal Rank Fusion."""
        fused_map: Dict[str, FusedCandidate] = {}
        sparse_candidates = sparse_candidates or []

        # 1. Index dense vector candidates
        for rank, vc in enumerate(vector_candidates):
            rrf_contrib = (vector_weight * 1.0) / (rrf_k + rank + 1)
            fused_map[vc.chunk_id] = FusedCandidate(
                chunk_id=vc.chunk_id,
                document_id=vc.document_id,
                document_title=vc.document_title,
                chunk_index=vc.chunk_index,
                page_number=vc.page_number,
                section_title=vc.section_title,
                content=vc.content,
                vector_score=vc.similarity_score,
                sparse_score=0.0,
                graph_score=0.0,
                rrf_score=rrf_contrib,
                final_score=0.0,
                origin="vector",
            )

        # 2. Index sparse BM25 keyword candidates
        for rank, sc in enumerate(sparse_candidates):
            rrf_contrib = (sparse_weight * 1.0) / (rrf_k + rank + 1)
            if sc.chunk_id in fused_map:
                existing = fused_map[sc.chunk_id]
                existing.sparse_score = sc.bm25_score
                existing.rrf_score += rrf_contrib
                existing.origin = "hybrid"
                existing.matched_keywords = list(set(existing.matched_keywords + sc.matched_terms))
            else:
                fused_map[sc.chunk_id] = FusedCandidate(
                    chunk_id=sc.chunk_id,
                    document_id=sc.document_id,
                    document_title=sc.document_title,
                    chunk_index=sc.chunk_index,
                    page_number=sc.page_number,
                    section_title=sc.section_title,
                    content=sc.content,
                    vector_score=0.0,
                    sparse_score=sc.bm25_score,
                    graph_score=0.0,
                    rrf_score=rrf_contrib,
                    final_score=0.0,
                    origin="sparse",
                    matched_keywords=sc.matched_terms,
                )

        # 3. Collect chunk IDs originating from graph search & paths
        graph_chunk_ids: Set[str] = set()
        chunk_to_entities: Dict[str, List[str]] = {}

        for gc in graph_candidates:
            for cid in gc.associated_chunk_ids:
                graph_chunk_ids.add(cid)
                chunk_to_entities.setdefault(cid, []).append(gc.canonical_name)

        for gp in graph_paths:
            for cid in gp.source_chunk_ids:
                graph_chunk_ids.add(cid)
                for n in gp.nodes:
                    chunk_to_entities.setdefault(cid, []).append(n["name"])

        # Fetch chunk content for graph chunks not yet in fused_map
        missing_chunk_ids = [cid for cid in graph_chunk_ids if cid not in fused_map]
        if missing_chunk_ids:
            stmt = (
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(DocumentChunk.id.in_(missing_chunk_ids[:50]))
            )
            rows = (await db.execute(stmt)).all()
            for rank, (chunk, doc) in enumerate(rows):
                rrf_contrib = (graph_weight * 1.0) / (rrf_k + rank + 1)
                fused_map[chunk.id] = FusedCandidate(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.original_filename or doc.filename,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_title=chunk.section_header,
                    content=chunk.content,
                    vector_score=0.0,
                    sparse_score=0.0,
                    graph_score=0.85,
                    rrf_score=rrf_contrib,
                    final_score=0.0,
                    origin="graph",
                    connected_entities=list(set(chunk_to_entities.get(chunk.id, []))),
                )

        # 4. Augment candidates that also matched graph entities
        for cid, cand in fused_map.items():
            if cid in graph_chunk_ids:
                cand.graph_score = 0.90
                cand.rrf_score += (graph_weight * 1.0) / (rrf_k + 1)
                cand.connected_entities = list(set(chunk_to_entities.get(cid, [])))

                if cand.vector_score > 0 and cand.sparse_score > 0:
                    cand.origin = "tri-hybrid"
                else:
                    cand.origin = "hybrid"

            # Compute combined final score
            # Balance vector similarity + BM25 keyword score + graph topology + scaled RRF bonus
            combined = (
                (cand.vector_score * vector_weight)
                + (cand.sparse_score * sparse_weight)
                + (cand.graph_score * graph_weight)
                + (cand.rrf_score * 10.0)
            )
            cand.final_score = round(combined, 4)

        # 5. Sort descending by final fused score
        fused_list = list(fused_map.values())
        fused_list.sort(key=lambda x: x.final_score, reverse=True)
        return fused_list
