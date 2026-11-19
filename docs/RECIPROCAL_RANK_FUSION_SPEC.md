# Reciprocal Rank Fusion (RRF) Hybrid Retrieval Specifications

## Overview
Combines dense vector similarity scores (pgvector) with sparse graph traversals (Neo4j).

## RRF Formulation
`RRF_Score(d) = sum(1.0 / (k + rank_i(d)))` where constant `k = 60`.

## Invariants
- Guarantees zero score starvation across multi-hop reasoning chains.
- Preserves top-k ranking invariant across sparse and dense retrievers.
