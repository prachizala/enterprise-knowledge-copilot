"""Reciprocal Rank Fusion (RRF) rank aggregation for hybrid vector & graph retrieval."""


class ReciprocalRankFusion:
    """Fuses multiple ranked candidate lists into a unified relevance score."""

    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, dense_ranks: list[str], graph_ranks: list[str]) -> list[tuple[str, float]]:
        """Computes combined RRF score: score(d) = sum(1 / (k + rank_i(d)))."""
        scores = {}
        for rank, doc_id in enumerate(dense_ranks, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (self.k + rank))

        for rank, doc_id in enumerate(graph_ranks, 1):
            scores[doc_id] = scores.get(doc_id, 0.0) + (1.0 / (self.k + rank))

        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
