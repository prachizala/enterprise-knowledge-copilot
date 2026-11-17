"""
Unit tests for Reciprocal Rank Fusion (RRF) and Hybrid GraphRAG Ranking.
"""

from scripts.benchmark_rrf import ReciprocalRankFusionEngine


def test_rrf_scoring_monotonicity():
    engine = ReciprocalRankFusionEngine(k=60)
    score_1 = engine.compute_rrf_score(1)
    score_2 = engine.compute_rrf_score(2)
    score_10 = engine.compute_rrf_score(10)
    score_none = engine.compute_rrf_score(None)

    assert score_1 > score_2 > score_10
    assert score_none == 0.0


def test_fused_rankings_priority():
    engine = ReciprocalRankFusionEngine(k=60)
    dense_results = [
        {"id": "doc-a", "title": "Doc A"},
        {"id": "doc-b", "title": "Doc B"},
    ]
    graph_results = [
        {"id": "doc-b", "title": "Doc B"},
        {"id": "doc-c", "title": "Doc C"},
    ]

    fused = engine.fuse_rankings(dense_results, graph_results)
    assert len(fused) == 3

    # Doc B appeared in both lists, so its combined RRF score must be strictly higher than single appearance docs
    assert fused[0].doc_id == "doc-b"
    assert fused[0].dense_rank == 2
    assert fused[0].graph_rank == 1
    assert fused[0].rrf_score > fused[1].rrf_score
