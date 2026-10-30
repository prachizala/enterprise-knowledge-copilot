"""Candidate Fusion: combines vector candidates, graph candidates, and multi-hop paths."""

import logging
from typing import Dict, List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk
from app.retrieval.schemas import (
    FusedCandidate,
    GraphCandidate,
    GraphPath,
    VectorCandidate,
)

logger = logging.getLogger(__name__)


class CandidateFusion:
    """Fuses heterogeneous retrieval candidates into a unified scored candidate pool."""

    @staticmethod
    async def fuse(
        db: AsyncSession,
        vector_candidates: List[VectorCandidate],
        graph_candidates: List[GraphCandidate],
        graph_paths: List[GraphPath],
        vector_weight: float = 0.50,
        graph_weight: float = 0.50,
        rrf_k: int = 60,
    ) -> List[FusedCandidate]:
        """Combine vector and graph chunk evidence using Reciprocal Rank Fusion and weighted scoring."""
        fused_map: Dict[str, FusedCandidate] = {}

        # 1. Index vector candidates
        for rank, vc in enumerate(vector_candidates):
            rrf_contrib = 1.0 / (rrf_k + rank + 1)
            fused_map[vc.chunk_id] = FusedCandidate(
                chunk_id=vc.chunk_id,
                document_id=vc.document_id,
                document_title=vc.document_title,
                chunk_index=vc.chunk_index,
                page_number=vc.page_number,
                section_title=vc.section_title,
                content=vc.content,
                vector_score=vc.similarity_score,
                graph_score=0.0,
                rrf_score=rrf_contrib,
                final_score=0.0,
                origin="vector",
            )

        # 2. Collect chunk IDs originating from graph search & paths
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

        # Fetch chunk content for graph chunks that were not in vector results
        missing_chunk_ids = [cid for cid in graph_chunk_ids if cid not in fused_map]
        if missing_chunk_ids:
            stmt = (
                select(DocumentChunk, Document)
                .join(Document, DocumentChunk.document_id == Document.id)
                .where(DocumentChunk.id.in_(missing_chunk_ids[:50]))
            )
            rows = (await db.execute(stmt)).all()
            for rank, (chunk, doc) in enumerate(rows):
                rrf_contrib = 1.0 / (rrf_k + rank + 1)
                fused_map[chunk.id] = FusedCandidate(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.original_filename or doc.filename,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    section_title=chunk.section_header,
                    content=chunk.content,
                    vector_score=0.0,
                    graph_score=0.85,
                    rrf_score=rrf_contrib,
                    final_score=0.0,
                    origin="graph",
                    connected_entities=list(set(chunk_to_entities.get(chunk.id, []))),
                )

        # 3. Augment vector candidates that also matched graph entities
        for cid, cand in fused_map.items():
            if cid in graph_chunk_ids:
                cand.graph_score = 0.90
                if cand.origin == "vector":
                    cand.origin = "hybrid"
                    # Add graph RRF contribution
                    cand.rrf_score += 1.0 / (rrf_k + 1)
                cand.connected_entities = list(set(chunk_to_entities.get(cid, [])))

            # Compute combined final score
            # Balance vector similarity + graph topology support + RRF bonus
            combined = (
                (cand.vector_score * vector_weight)
                + (cand.graph_score * graph_weight)
                + (cand.rrf_score * 10.0)  # Scale RRF
            )
            cand.final_score = round(combined, 4)

        # 4. Sort descending by final fused score
        fused_list = list(fused_map.values())
        fused_list.sort(key=lambda x: x.final_score, reverse=True)
        return fused_list
