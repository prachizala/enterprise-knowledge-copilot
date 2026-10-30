# Enterprise Knowledge Copilot — Architecture Overview

## 1. Vision & Strategy

Enterprise Knowledge Copilot is a production-grade knowledge retrieval and reasoning platform that bridges relational knowledge graphs (Neo4j), vector similarity search, and high-performance relational storage (PostgreSQL) using Hybrid GraphRAG techniques.

```
                           +------------------------------+
                           |       Next.js Frontend       |
                           |    (TypeScript + Tailwind)   |
                           +--------------+---------------+
                                          |
                                          | HTTP / REST
                                          v
                           +------------------------------+
                           |       FastAPI Backend        |
                           |  (App, Core, API, Services)  |
                           +---+----------+-----------+---+
                               |          |           |
            +------------------+          |           +------------------+
            |                             |                              |
            v                             v                              v
+-----------------------+     +-----------------------+      +-----------------------+
|  PostgreSQL Database  |     |  Neo4j Graph Database |      |  LLM & Vector Engine  |
|  - Users & Workspaces |     |  - Entity Ontologies  |      |  - Dense Embeddings   |
|  - Documents & Chunks |     |  - Relationship Graph |      |  - Hybrid RAG Fusion  |
|  - Audit Log Trails   |     |  - Subgraph Traversal |      |  - Citation Verify    |
+-----------------------+     +-----------------------+      +-----------------------+
```

## 2. Directory Layout & Module Responsibilities

- **`backend/app/api/`**: API route declarations, versioning (`/api/health`, `/api/v1`), dependency injection, and middleware.
- **`backend/app/core/`**: Configuration management using Pydantic Settings, environment variable loading, security tokens, and logging.
- **`backend/app/models/`**: PostgreSQL and relational models (SQLAlchemy / SQLModel).
- **`backend/app/schemas/`**: Pydantic validation schemas for API inputs and outputs.
- **`backend/app/services/`**: Integration services (Neo4j driver, PostgreSQL connection pool, LLM providers).
- **`backend/app/ingestion/`**: Document ingestion parsers (PDF, DOCX, TXT, CSV) and semantic chunking.
- **`backend/app/extraction/`**: Entity and relationship extraction from document chunks to form graph nodes and edges.
- **`backend/app/embeddings/`**: Vector embedding generation and similarity index operations.
- **`backend/app/graph/`**: Cypher query construction, graph algorithms, and sub-graph neighborhood extraction.
- **`backend/app/retrieval/`**: Hybrid retrieval pipeline combining vector semantic search, BM25 keyword matching, and graph traversal with Reciprocal Rank Fusion (RRF).
- **`backend/app/generation/`**: Grounded generation prompts, LLM inference, and verifiable source citation attribution.

## 3. Step 1 Foundation Status

- FastAPI application configured with `/` and `/api/health` endpoints.
- Settings system configured to bind PostgreSQL, Neo4j, and LLM credentials via environment variables without creating active connections.
- Next.js 14 frontend created with TypeScript, Tailwind CSS, placeholders for chat and knowledge graph visualizer, and system status monitor.
- Docker Compose configuration orchestrating frontend, backend, PostgreSQL, and Neo4j.
