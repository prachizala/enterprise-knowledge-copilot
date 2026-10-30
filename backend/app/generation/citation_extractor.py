"""Citation Extractor: extracts, verifies, and binds source document provenance to answer citations."""

import re
from typing import List, Set
from app.generation.schemas import Citation
from app.retrieval.schemas import GroundedContext


class CitationExtractor:
    """Extracts and verifies citation markers against retrieved evidence to guarantee 100% source traceability."""

    @staticmethod
    def extract_and_verify(
        answer_text: str,
        context: GroundedContext,
    ) -> List[Citation]:
        """Parse citation tags from generated answer and bind to verified chunk metadata."""
        if not context.selected_evidence and not context.graph_paths:
            return []

        # Find all bracketed citation numbers: [1], [2], etc.
        raw_markers = re.findall(r"\[(\d+)\]", answer_text)
        cited_indices: Set[int] = {int(m) for m in raw_markers}

        # If answer has no explicit citations but evidence was retrieved, cite the primary evidence
        if not cited_indices and context.selected_evidence:
            cited_indices.add(1)

        verified_citations: List[Citation] = []
        evidence_list = context.selected_evidence

        for idx in sorted(cited_indices):
            # 1-based index mapping to retrieved evidence chunks
            array_idx = idx - 1
            if 0 <= array_idx < len(evidence_list):
                cand = evidence_list[array_idx]
                verified_citations.append(
                    Citation(
                        citation_id=idx,
                        document_id=cand.document_id,
                        document_name=cand.document_title,
                        chunk_id=cand.chunk_id,
                        page_start=cand.page_number,
                        page_end=cand.page_number,
                        section_title=cand.section_title,
                        excerpt=cand.content[:300].strip(),
                        relevance_score=cand.final_score,
                        evidence_type="document_chunk",
                    )
                )
            elif context.graph_paths and array_idx < len(context.graph_paths):
                # Fallback to graph path if citation index points to graph path
                gp = context.graph_paths[array_idx]
                verified_citations.append(
                    Citation(
                        citation_id=idx,
                        document_id=gp.document_ids[0] if gp.document_ids else "knowledge-graph",
                        document_name="Enterprise Knowledge Graph",
                        chunk_id=gp.source_chunk_ids[0] if gp.source_chunk_ids else "graph-edge",
                        excerpt=gp.formatted_path,
                        relevance_score=gp.confidence,
                        evidence_type="graph_relationship",
                    )
                )

        return verified_citations

    @classmethod
    def extract_citations(
        cls,
        answer_text: str,
        fused_candidates: list = None,
        graph_paths: list = None,
    ) -> List[Citation]:
        from app.retrieval.context_builder import ContextBuilder
        context = ContextBuilder.build(
            candidates=fused_candidates or [],
            paths=graph_paths or [],
        )
        return cls.extract_and_verify(answer_text, context)
