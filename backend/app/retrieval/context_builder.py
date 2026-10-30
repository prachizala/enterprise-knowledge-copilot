"""Context Builder: constructs secure, grounded context payloads for LLM generation."""

from typing import Dict, List
from app.core.config import settings
from app.retrieval.schemas import (
    FusedCandidate,
    GroundedContext,
    GraphCandidate,
    GraphPath,
    LinkedEntity,
    QueryAnalysis,
    VectorCandidate,
)


class ContextBuilder:
    """Formats verified evidence chunks and graph relationship paths into a structured context payload."""

    @classmethod
    def build(
        cls,
        candidates: List[FusedCandidate] = None,
        paths: List[GraphPath] = None,
        query: str = "Query",
    ) -> GroundedContext:
        """Convenience method to construct GroundedContext directly from candidates and paths."""
        qa = QueryAnalysis(
            raw_query=query,
            normalized_query=query.lower(),
            query_category="factual_lookup",
        )
        return cls.build_context(
            query=query,
            query_analysis=qa,
            linked_entities=[],
            vector_candidates=[],
            graph_candidates=[],
            graph_paths=paths or [],
            selected_evidence=candidates or [],
            latencies={},
        )

    @staticmethod
    def build_context(
        query: str,
        query_analysis: QueryAnalysis,
        linked_entities: List[LinkedEntity],
        vector_candidates: List[VectorCandidate],
        graph_candidates: List[GraphCandidate],
        graph_paths: List[GraphPath],
        selected_evidence: List[FusedCandidate],
        latencies: Dict[str, float],
        max_characters: int = 12000,
        max_chunks: int = 10,
    ) -> GroundedContext:
        """Construct structured prompt context ensuring strict security boundaries and character limits."""
        lines: List[str] = []

        # 1. Grounded Knowledge Graph Reasoning Paths
        if graph_paths:
            lines.append("=== VERIFIED KNOWLEDGE GRAPH PATHS ===")
            for i, gp in enumerate(graph_paths[: settings.GRAPHRAG_MAX_PATHS], 1):
                evidence_note = f" (Evidence: '{gp.evidence_texts[0]}')" if gp.evidence_texts else ""
                lines.append(f"[{i}] {gp.formatted_path}{evidence_note} [Confidence: {gp.confidence}]")
            lines.append("")

        # 2. Direct Graph Entity Relationships
        if graph_candidates:
            lines.append("=== DIRECT ENTITY ATTRIBUTES & RELATIONSHIPS ===")
            for gc in graph_candidates[: settings.GRAPHRAG_MAX_GRAPH_ENTITIES]:
                for r in gc.direct_relationships[:5]:
                    lines.append(
                        f"- {gc.canonical_name} ({gc.entity_type}) -[:{r['relationship_type']}]-> "
                        f"{r['target_name']} ({r['target_type']}) [Confidence: {r['confidence']}]"
                    )
            lines.append("")

        # 3. Grounded Document Evidence Excerpts (with isolation tags to prevent prompt injection)
        lines.append("=== GROUNDED ENTERPRISE DOCUMENT EXCERPTS ===")
        total_chars = sum(len(l) for l in lines)
        chunks_included = 0

        for cand in selected_evidence[:max_chunks]:
            page_info = f"page={cand.page_number}" if cand.page_number else "page=N/A"
            section_info = f'section="{cand.section_title}"' if cand.section_title else ""
            header = f'<<<DOCUMENT_EXCERPT: doc_id="{cand.document_id}" chunk_id="{cand.chunk_id}" title="{cand.document_title}" {page_info} {section_info}>>>'
            footer = "<<<END_DOCUMENT_EXCERPT>>>"

            entry_text = f"{header}\n{cand.content.strip()}\n{footer}\n"
            if total_chars + len(entry_text) > max_characters and chunks_included > 0:
                break

            lines.append(entry_text)
            total_chars += len(entry_text)
            chunks_included += 1

        formatted_context = "\n".join(lines)

        return GroundedContext(
            query=query,
            query_analysis=query_analysis,
            linked_entities=linked_entities,
            vector_candidates_count=len(vector_candidates),
            graph_candidates_count=len(graph_candidates),
            graph_paths=graph_paths,
            selected_evidence=selected_evidence[:chunks_included],
            formatted_context_str=formatted_context,
            total_characters=len(formatted_context),
            total_chunks=chunks_included,
            latency_ms=latencies,
        )
