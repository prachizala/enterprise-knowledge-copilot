"""GraphRAG Retrieval Service: coordinates query understanding, entity linking, vector search, graph expansion, fusion, reranking, and context building."""

import logging
import time
from typing import List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import build_accessible_documents_filter
from app.core.config import settings
from app.models.document import Document
from app.retrieval.candidate_fusion import CandidateFusion
from app.retrieval.context_builder import ContextBuilder
from app.retrieval.diversification import DiversificationService
from app.retrieval.entity_linker import EntityLinker
from app.retrieval.graph_expander import GraphExpander
from app.retrieval.graph_search import GraphSearchService
from app.retrieval.keyword_search import KeywordSearchService
from app.retrieval.query_analyzer import QueryAnalyzer
from app.retrieval.reranker import DeterministicReranker
from app.retrieval.schemas import (
    FusedCandidate,
    GroundedContext,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
)
from app.retrieval.vector_search import VectorSearchService

logger = logging.getLogger(__name__)


class GraphRAGRetrievalService:
    """Master orchestrator for Advanced GraphRAG retrieval."""

    def __init__(self) -> None:
        self.query_analyzer = QueryAnalyzer()
        self.entity_linker = EntityLinker()
        self.graph_search = GraphSearchService()
        self.graph_expander = GraphExpander()
        self.fusion = CandidateFusion()
        self.reranker = DeterministicReranker()
        self.diversification = DiversificationService()
        self.context_builder = ContextBuilder()

    async def retrieve(
        self,
        db: AsyncSession,
        query: str,
        user: Optional[object] = None,
        top_k: int = 10,
        min_similarity: float = 0.20,
        department: Optional[str] = None,
        document_id: Optional[str] = None,
        depth: int = 2,
        include_graph: bool = True,
        vector_weight: float = 0.40,
        sparse_weight: float = 0.30,
        graph_weight: float = 0.30,
        rrf_k: int = 60,
    ) -> GroundedContext:
        """Execute full end-to-end Tri-Hybrid GraphRAG retrieval pipeline and return grounded context."""
        latencies = {}
        t_total_start = time.perf_counter()

        # 1. Query Analysis
        t_start = time.perf_counter()
        analysis = self.query_analyzer.analyze(query)
        latencies["query_analysis_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # Merge extracted department/doc filters
        effective_department = department or analysis.extracted_filters.get("department")
        effective_doc_id = document_id or analysis.extracted_filters.get("document_id")

        # 2. Entity Linking
        t_start = time.perf_counter()
        linked_entities = await self.entity_linker.link_mentions(
            db=db,
            mentions=analysis.detected_entities,
        )
        latencies["entity_linking_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # 3. Resolve accessible document IDs for current user (Phase 20 RBAC)
        t_start = time.perf_counter()
        allowed_doc_ids: Optional[Set[str]] = None
        if user is not None:
            rbac_filter = build_accessible_documents_filter(user)
            if rbac_filter is not None:
                doc_stmt = select(Document.id).where(rbac_filter)
                allowed_doc_ids = set((await db.execute(doc_stmt)).scalars().all())

        # 4. Dense Vector Retrieval
        t_vec_start = time.perf_counter()
        vector_candidates = await VectorSearchService.search_candidates(
            db=db,
            query=query,
            user=user,
            top_k=top_k * 2,
            min_similarity=min_similarity,
            department=effective_department,
            document_id=effective_doc_id,
        )
        latencies["vector_retrieval_ms"] = round((time.perf_counter() - t_vec_start) * 1000, 2)

        # 4b. Sparse Lexical Retrieval (BM25)
        t_sparse_start = time.perf_counter()
        sparse_candidates = await KeywordSearchService.search_candidates(
            db=db,
            query=query,
            user=user,
            top_k=top_k * 2,
            department=effective_department,
            document_id=effective_doc_id,
        )
        latencies["sparse_retrieval_ms"] = round((time.perf_counter() - t_sparse_start) * 1000, 2)

        # 5. Graph Retrieval & Multi-hop Expansion
        graph_candidates = []
        graph_paths = []
        if include_graph and linked_entities:
            t_graph_start = time.perf_counter()
            graph_candidates = await self.graph_search.search_entities(
                linked_entities=linked_entities,
                allowed_document_ids=allowed_doc_ids,
            )
            latencies["graph_search_ms"] = round((time.perf_counter() - t_graph_start) * 1000, 2)

            t_hop_start = time.perf_counter()
            graph_paths = await self.graph_expander.expand_paths(
                linked_entities=linked_entities,
                depth=depth,
                max_paths=settings.GRAPHRAG_GRAPH_MAX_PATHS,
                allowed_document_ids=allowed_doc_ids,
            )
            latencies["multi_hop_expansion_ms"] = round((time.perf_counter() - t_hop_start) * 1000, 2)
        else:
            latencies["graph_search_ms"] = 0.0
            latencies["multi_hop_expansion_ms"] = 0.0

        # 6. Candidate Fusion (Tri-Hybrid RRF + Weighted)
        t_start = time.perf_counter()
        fused = await self.fusion.fuse(
            db=db,
            vector_candidates=vector_candidates,
            graph_candidates=graph_candidates,
            graph_paths=graph_paths,
            sparse_candidates=sparse_candidates,
            vector_weight=vector_weight,
            sparse_weight=sparse_weight,
            graph_weight=graph_weight,
            rrf_k=rrf_k,
        )
        latencies["candidate_fusion_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # 7. Advanced Reranking
        t_start = time.perf_counter()
        reranked = await self.reranker.rerank(
            query=query,
            candidates=fused,
            linked_entities=linked_entities,
            top_n=top_k * 2,
        )
        latencies["reranking_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # 8. Diversification & MMR Selection
        t_start = time.perf_counter()
        selected_evidence = self.diversification.diversify(
            candidates=reranked,
            max_chunks_per_document=3,
            total_limit=top_k,
        )
        latencies["diversification_ms"] = round((time.perf_counter() - t_start) * 1000, 2)

        # 9. Context Construction
        latencies["total_retrieval_ms"] = round((time.perf_counter() - t_total_start) * 1000, 2)
        grounded_context = self.context_builder.build_context(
            query=query,
            query_analysis=analysis,
            linked_entities=linked_entities,
            vector_candidates=vector_candidates,
            graph_candidates=graph_candidates,
            graph_paths=graph_paths,
            selected_evidence=selected_evidence,
            latencies=latencies,
            max_characters=settings.GRAPHRAG_MAX_CONTEXT_CHARACTERS,
            max_chunks=settings.GRAPHRAG_MAX_CONTEXT_CHUNKS,
        )

        return grounded_context


# Singleton instance
retrieval_service = GraphRAGRetrievalService()
