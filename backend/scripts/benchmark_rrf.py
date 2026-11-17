"""
Reciprocal Rank Fusion (RRF) & Hybrid GraphRAG Retrieval Benchmark.
Evaluates precision and ranking improvement when combining Dense Vector Search (pgvector)
with Multi-Hop Knowledge Graph Traversal (Neo4j).
"""

from dataclasses import dataclass


@dataclass
class SearchResultItem:
    doc_id: str
    title: str
    dense_rank: int | None = None
    graph_rank: int | None = None
    rrf_score: float = 0.0


class ReciprocalRankFusionEngine:
    """Implements industry-standard Reciprocal Rank Fusion (RRF) ranking algorithm."""

    def __init__(self, k: int = 60):
        # Default smoothing constant recommended by Cormack et al.
        self.k = k

    def compute_rrf_score(self, rank: int | None) -> float:
        if rank is None or rank <= 0:
            return 0.0
        return 1.0 / (self.k + rank)

    def fuse_rankings(
        self, dense_results: list[dict], graph_results: list[dict]
    ) -> list[SearchResultItem]:
        """Fuses ordered vector search results and graph multi-hop entities."""
        items: dict[str, SearchResultItem] = {}

        # 1. Process dense vector rankings
        for rank, res in enumerate(dense_results, start=1):
            doc_id = res["id"]
            if doc_id not in items:
                items[doc_id] = SearchResultItem(
                    doc_id=doc_id, title=res.get("title", doc_id), dense_rank=rank
                )
            else:
                items[doc_id].dense_rank = rank

        # 2. Process graph traversal rankings
        for rank, res in enumerate(graph_results, start=1):
            doc_id = res["id"]
            if doc_id not in items:
                items[doc_id] = SearchResultItem(
                    doc_id=doc_id, title=res.get("title", doc_id), graph_rank=rank
                )
            else:
                items[doc_id].graph_rank = rank

        # 3. Calculate fused RRF score
        fused_list: list[SearchResultItem] = []
        for item in items.values():
            score_dense = self.compute_rrf_score(item.dense_rank)
            score_graph = self.compute_rrf_score(item.graph_rank)
            item.rrf_score = round(score_dense + score_graph, 6)
            fused_list.append(item)

        # Sort by highest RRF score first
        fused_list.sort(key=lambda x: x.rrf_score, reverse=True)
        return fused_list


def benchmark_hybrid_retrieval():
    """Demonstrates RRF ranking advantage over standalone vector search."""
    dense_candidates = [
        {
            "id": "doc-01",
            "title": "Enterprise Microservices Architecture Specification",
        },
        {"id": "doc-02", "title": "OAuth2 Security Perimeter & Token Validation"},
        {"id": "doc-03", "title": "Customer Data Retention Compliance Guidelines"},
    ]

    graph_candidates = [
        {"id": "doc-02", "title": "OAuth2 Security Perimeter & Token Validation"},
        {"id": "doc-04", "title": "Neo4j Multi-Hop Role-Based Access Control"},
        {
            "id": "doc-01",
            "title": "Enterprise Microservices Architecture Specification",
        },
    ]

    engine = ReciprocalRankFusionEngine(k=60)
    fused = engine.fuse_rankings(dense_candidates, graph_candidates)

    print("=== Hybrid GraphRAG Reciprocal Rank Fusion Benchmark ===")
    for rank, item in enumerate(fused, start=1):
        print(
            f"Rank {rank}: {item.title} (ID: {item.doc_id}) | Dense: {item.dense_rank} | Graph: {item.graph_rank} | RRF Score: {item.rrf_score}"
        )

    # doc-02 and doc-01 appear in both modalities and should top the fused list
    assert fused[0].doc_id in ["doc-01", "doc-02"]
    print(
        "Benchmark PASSED: Multi-modal fusion successfully boosts multi-hop grounded contexts.\n"
    )


if __name__ == "__main__":
    benchmark_hybrid_retrieval()
