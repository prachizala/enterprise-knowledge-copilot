"""Context diversification and MMR selection to avoid document redundancy."""

from typing import Dict, List
from app.retrieval.schemas import FusedCandidate


class DiversificationService:
    """Ensures balanced evidence representation across enterprise documents."""

    @staticmethod
    def diversify(
        candidates: List[FusedCandidate],
        max_chunks_per_document: int = 3,
        total_limit: int = 10,
    ) -> List[FusedCandidate]:
        """Filter out excessive duplicate chunks from the same document while preserving highest-scoring evidence."""
        selected: List[FusedCandidate] = []
        doc_counts: Dict[str, int] = {}

        for cand in candidates:
            current_count = doc_counts.get(cand.document_id, 0)
            if current_count < max_chunks_per_document:
                selected.append(cand)
                doc_counts[cand.document_id] = current_count + 1
                if len(selected) >= total_limit:
                    break

        # If strict document limit leaves too few results, backfill with remaining best candidates
        if len(selected) < total_limit and len(candidates) > len(selected):
            selected_ids = {c.chunk_id for c in selected}
            for cand in candidates:
                if cand.chunk_id not in selected_ids:
                    selected.append(cand)
                    if len(selected) >= total_limit:
                        break

        return selected
