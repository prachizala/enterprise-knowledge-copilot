# Changes Log - enterprise-knowledge-copilot (enterprise-graphrag)

## Summary of Changes
- **Branch:** `review-fixes` (created from `main`)
- **In-Memory Structured Mock Graph Fallback:**
  - Added `backend/app/graph/mock_store.py` providing an in-memory mock knowledge graph store (`MockGraphStore`) containing enterprise entities, relationships, and Cypher query interpretation for entity lookups, relationship traversals, subgraphs, and health checks.
  - Added `MOCK_NEO4J: bool = False` to `backend/app/core/config.py` (and `.env.example`).
  - Updated `Neo4jClient` in `backend/app/graph/client.py` with automatic, graceful fallback: if `MOCK_NEO4J=True` or if the Neo4j instance is unreachable, it logs a warning and activates the in-memory mock store rather than crashing with unhandled connection errors.
- **Automated Verification:**
  - Added dedicated test suite `backend/tests/test_mock_neo4j.py` testing:
    * Forced mock mode via `settings.MOCK_NEO4J = True`.
    * Automatic fallback when connecting to an unreachable Neo4j URI.
    * Graph repository entity search, entity detail, and subgraph extraction under mock mode.
  - Ran `pytest tests/test_mock_neo4j.py`: 3 passed.
  - Ran existing `pytest tests/test_graph.py`: 17 passed.
- **Documentation:**
  - Updated `README.md` under "Local Development Setup" with a new subsection "Local Development without Docker (`MOCK_NEO4J=true`)" explaining setup and benefits for low-resource environments.
  - Updated `.env.example` with the `MOCK_NEO4J` parameter.

## Skipped Items
- None. All requested tasks for this repository have been completed and verified.

## Manual Steps Needed
- To run locally without Docker or Neo4j, set `MOCK_NEO4J=true` in `.env` or your shell.
