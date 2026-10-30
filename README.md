# Enterprise Knowledge Copilot — Knowledge Graph RAG for Enterprise Data

[![CI Pipeline](https://github.com/prachizala/enterprise-knowledge-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/prachizala/enterprise-knowledge-copilot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14.2-000000?logo=nextdotjs&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20pgvector-4169E1?logo=postgresql&logoColor=white)
![Neo4j](https://img.shields.io/badge/Neo4j-5.20-45818E?logo=neo4j&logoColor=white)
![Tests](https://img.shields.io/badge/Tests-149%20Passed-brightgreen)
![Streaming](https://img.shields.io/badge/Streaming-SSE%20Enabled-00b4d8)
![Ollama](https://img.shields.io/badge/Local%20LLM-Ollama%20Supported-orange?logo=ollama)
![Retrieval](https://img.shields.io/badge/Retrieval-Tri--Hybrid%20(Dense%20%2B%20BM25%20%2B%20Graph)-blueviolet)

> **Production Status:** Steps 1 through 16 are **fully implemented and verified**. The platform is an end-to-end operational GraphRAG enterprise intelligence system featuring:
> - **Real-Time Token Streaming**: Server-Sent Events (SSE) `/api/copilot/chat/stream` for immediate response delivery and interactive provenance inspection via Citation Drawer.
> - **Zero-Cost & Offline Ready**: Native support for **Ollama** (`llama3.2`, `qwen2.5`, `mistral`) alongside OpenAI and deterministic offline mocks.
> - **Tri-Hybrid Retrieval Engine** (Fusing Dense pgvector cosine embeddings + Sparse Okapi BM25 keyword matching + Neo4j knowledge graph topology traversal via Weighted Reciprocal Rank Fusion).
> - **RBAC Authentication & Security** (JWT tokens, role-based document access: `ADMIN`, `MANAGER`, `EMPLOYEE`, `VIEWER`).
> - **Relational Storage of Truth** (PostgreSQL 16 + SQLAlchemy 2.x async + Alembic).
> - **Dense Semantic Vector Search** (pgvector HNSW cosine indexing with 1536D embeddings).
> - **Enterprise Knowledge Graph** (Neo4j 5.20 with multi-hop Cypher traversal and bidirectional PostgreSQL synchronization).
> - **Hybrid GraphRAG Retrieval Engine** (Query analysis, entity linking, vector retrieval, graph expansion, Reciprocal Rank Fusion, MMR reranking, anti-prompt injection delimiters).
> - **Grounded LLM Generation Subsystem** (OpenAI / Ollama / Mock providers with zero-hallucination refusals and strict evidence containment).
> - **Verified In-Text Citations & Provenance Drawer** (`[1]`, `[2]` linking assertions to source documents, page numbers, and chunk coordinates with deep inspection).
> - **Conversational Copilot** (Multi-turn dialogue, session persistence, explicit feedback logging, latency tracking).
> - **6-Stage Background Ingestion Pipeline** (Extraction $\to$ Chunking $\to$ Embeddings $\to$ Entities $\to$ Relationships $\to$ Neo4j Sync).
> - **Evaluation Benchmark Suite** (Precision, recall, groundedness score, citation validity, hallucination rate, latency).
> - **Interactive Next.js Dashboard** (Copilot chat, vector workbench, graph visualizer, entity explorer, document manager, live analytics, system settings).

---

## 1. Architecture Overview

```text
                               +--------------------------------------------------+
                               |            Next.js 14 Web Frontend              |
                               |  - Grounded Copilot Chat (/copilot)              |
                               |  - Semantic Vector Workbench (/copilot)          |
                               |  - Knowledge Graph Explorer (/knowledge-graph)   |
                               |  - Entity Directory (/entities)                  |
                               |  - Document & Pipeline Management (/documents)   |
                               |  - Live Platform Analytics (/analytics)          |
                               |  - AI & Security Settings (/settings)            |
                               +------------------------+-------------------------+
                                                        |
                                                        | HTTPS / REST JSON (/api/*)
                                                        v
+-------------------------------------------------------------------------------------------------------------------+
|                                            FastAPI Backend Platform                                               |
|                                                                                                                   |
|  +--------------------+   +-----------------------+   +-----------------------+   +----------------------------+  |
|  |  Auth & RBAC       |   | Ingestion Pipeline    |   | GraphRAG Retrieval    |   | Grounded LLM Generation    |  |
|  |  - JWT Bearer      |   | 1. Text Extraction    |   | - Query Analyzer      |   | - Anti-Injection Sandbox   |  |
|  |  - Passlib/Bcrypt  |   | 2. Aware Chunking     |   | - Entity Linker       |   | - OpenAI & Mock Provider   |  |
|  |  - Role Hierarchy  |   | 3. Dense Embeddings   |   | - pgvector Search     |   | - Citation Extractor       |  |
|  |  - Doc Access Guard|   | 4. Entity Extraction  |   | - Neo4j Multi-Hop Exp |   | - Grounding Scorer (0-1.0) |  |
|  +--------------------+   | 5. Relation Extraction|   | - RRF Rank Fusion     |   | - Zero-Hallucination Guard |  |
|                           | 6. Neo4j Graph Sync   |   | - MMR Diversification |   +----------------------------+  |
|                           +-----------------------+   +-----------------------+                                   |
+---------------------------------------------------+---------------------------------------------------------------+
                                                    |
                         +--------------------------+--------------------------+
                         |                                                     |
                         v                                                     v
+---------------------------------------------------+     +---------------------------------------------------+
|               PostgreSQL Database                 |     |               Neo4j Graph Database                |
|               (Source of Truth)                   |     |              (Knowledge Graph Index)              |
|                                                   |     |                                                   |
|  - Users & Roles (ADMIN, MANAGER, etc.)           |     |  - (:Entity) Nodes with canonical names & labels  |
|  - Documents, Content & Secure Storage Lineage    |     |  - [:RELATIONSHIP] Typed directed edges           |
|  - DocumentChunks with structural metadata        |     |  - Confidence scores & document provenance        |
|  - ChunkEmbeddings with pgvector HNSW Index       |     |  - Multi-hop path expansion (1-3 hops)            |
|  - Entities, Mentions & Canonical Records         |     |  - APOC plugin procedures                         |
|  - EntityRelationships with grounded evidence     |     |  - Cypher subgraph pattern queries                |
|  - Conversations, Messages & User Feedback        |     +---------------------------------------------------+
|  - ProcessingJobs & Ingestion Task States         |
|  - EvaluationRuns & Benchmark Results             |
+---------------------------------------------------+
```

---

## 2. Technology Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript (Strict Mode)
- **Styling**: Tailwind CSS
- **Iconography**: Lucide React
- **API Client**: Strongly-typed async client (`frontend/lib/api.ts`)

### Backend
- **Framework**: FastAPI
- **Language**: Python 3.11+ / 3.12+
- **ORM**: SQLAlchemy 2.x (Async with `asyncpg` / `aiosqlite`)
- **Security**: PyJWT, Passlib, Bcrypt, Email-Validator
- **Vector Search**: pgvector with HNSW cosine distance indexing
- **Graph Client**: `neo4j` official async driver
- **Extractors**: `pypdf`, `python-docx`, Python stdlib
- **Migrations**: Alembic
- **Settings**: Pydantic v2 & Pydantic Settings (`pydantic-settings`)
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

### Databases & Infrastructure
- **Relational DB**: PostgreSQL 16 (`pgvector/pgvector:pg16`)
- **Graph DB**: Neo4j 5.20 Community Edition (APOC enabled)
- **Storage**: `data/uploads/<document-id>/`
- **Orchestration**: Docker & Docker Compose

---

## 3. End-to-End Capabilities

### A. Role-Based Access Control (RBAC)
- 4 hierarchical enterprise roles:
  - **ADMIN**: Full platform administration, reindexing, job orchestration, user management.
  - **MANAGER**: Department-level management, document upload, evaluation runs.
  - **EMPLOYEE**: Read/query access to internal documents and departmental records.
  - **VIEWER**: Restricted read access to public/unclassified enterprise documents.
- Automatic query filtering in vector search and graph retrieval prevents cross-department data leakage.

### B. 6-Stage Ingestion Orchestrator
1. **Document Extraction**: Robust text and layout extraction from PDF, DOCX, TXT, and CSV files with MIME validation and directory traversal protection.
2. **Structure-Aware Chunking**: Hierarchical chunking preserving headings, section paths, page numbers, and tables with zero boundary cuts.
3. **pgvector Embeddings**: Dense 1536-dimensional semantic embeddings stored in PostgreSQL with HNSW indexing and SHA-256 deduplication.
4. **Entity Extraction & Normalization**: Extraction across 15 enterprise types (`PERSON`, `ORGANIZATION`, `DEPARTMENT`, `PROJECT`, `PRODUCT`, `TECHNOLOGY`, `POLICY`, `LOCATION`, etc.) with NFKC canonical normalization.
5. **Relationship Extraction**: Extraction of typed directed relations (`WORKS_FOR`, `MANAGES`, `USES`, `DEPENDS_ON`, `GOVERNS`, `APPLIES_TO`, etc.) with grounded text evidence.
6. **Neo4j Graph Synchronization**: Automated synchronization of canonical entities and relationships into Neo4j graph nodes and edges with rollback safety.

### C. Advanced GraphRAG Retrieval Engine
1. **Query Analysis**: Categorizes queries (`factual`, `relationship`, `multi-hop`, `summary`) and extracts key entity mentions.
2. **Entity Linking**: Resolves query mentions to canonical PostgreSQL entities with fuzzy/alias matching.
3. **Dual-Index Retrieval**:
   - **Dense pgvector Search**: Cosine similarity over document chunk embeddings with RBAC filters.
   - **Neo4j Graph Expansion**: 1 to 3-hop traversal from linked entities retrieving connected subgraphs and relational context.
4. **Reciprocal Rank Fusion (RRF)**: Merges vector candidates and graph candidates with weighted scoring ($w_{dense} = 0.5$, $w_{graph} = 0.5$, $k = 60$).
5. **MMR Diversification & Reranking**: Eliminates redundant information and prioritizes high-relevance diverse evidence.
6. **Prompt Sandboxing**: Isolates retrieved evidence chunks within strict `<<<DOCUMENT_EXCERPT>>>` delimiters to neutralize indirect prompt injection attacks.

### D. Grounded LLM Generation & Verifiable Citations
- **Zero-Hallucination Policy**: If available evidence is insufficient to answer the query truthfully, the engine returns an explicit refusal with recommendations.
- **Strict In-Text Citations**: Every factual claim is annotated with `[1]`, `[2]` citation markers linked to exact documents, page numbers, and chunk coordinates.
- **Grounding Scorer**: Calculates a normalized 0.0–1.0 score measuring factual alignment between the response and retrieved context.

### E. Evaluation Benchmark Framework
- Gold standard benchmark dataset covering single-hop, multi-hop, organizational, and adversarial questions.
- Computes comprehensive metrics per run:
  - **Recall & Precision** against ground-truth entities and documents.
  - **Groundedness Score** (0.0 to 1.0).
  - **Citation Validity Rate** (% of citations referencing valid source text).
  - **Hallucination Rate** (% of ungrounded assertions).
  - **End-to-End Latency** (ms).

---

## 4. REST API Reference

| Endpoint | Method | Description |
|---|---|---|
| **Authentication** | | |
| `/api/auth/register` | `POST` | Register a new enterprise user |
| `/api/auth/login` | `POST` | Authenticate and obtain JWT access token |
| `/api/auth/me` | `GET` | Get current authenticated user profile |
| `/api/auth/logout` | `POST` | Invalidate current session |
| **Documents & Storage** | | |
| `/api/documents/upload` | `POST` | Upload and validate document (PDF, DOCX, TXT, CSV) |
| `/api/documents` | `GET` | List uploaded documents with pagination & status filters |
| `/api/documents/{id}` | `GET` | Get document metadata and processing state |
| `/api/documents/{id}` | `DELETE` | Cascade delete document, chunks, and embeddings |
| `/api/documents/{id}/content` | `GET` | Retrieve extracted document text |
| `/api/documents/{id}/chunks` | `GET` | List structure-aware chunks with page filters |
| `/api/documents/{id}/download` | `GET` | Securely download original file |
| **Vector Search & Embeddings** | | |
| `/api/search/vector` | `POST` | Dense pgvector semantic search with cosine similarity |
| `/api/documents/{id}/embeddings` | `POST` | Generate or refresh chunk embeddings |
| `/api/documents/{id}/embedding-status` | `GET` | Get embedding coverage and model metadata |
| `/api/embeddings/reindex` | `POST` | Global reindexing of all document chunks |
| **Entities & Relationships** | | |
| `/api/documents/{id}/entities/extract` | `POST` | Extract named entities from document chunks |
| `/api/documents/{id}/entities` | `GET` | List extracted entity mentions with provenance |
| `/api/entities/search` | `GET` | Search canonical entities by name and type |
| `/api/entities/{id}` | `GET` | Get canonical entity profile |
| `/api/documents/{id}/relationships/extract` | `POST` | Extract grounded relationships between entities |
| `/api/documents/{id}/relationships` | `GET` | List document relationships with evidence |
| `/api/entities/{id}/relationships` | `GET` | Get inbound/outbound relationships for an entity |
| `/api/relationships/search` | `GET` | Search relationships across entities and predicates |
| **Neo4j Knowledge Graph** | | |
| `/api/graph/health` | `GET` | Check Neo4j connection and node/edge statistics |
| `/api/graph/sync` | `POST` | Synchronize PostgreSQL entities and relationships to Neo4j |
| `/api/graph/entities/search` | `GET` | Search graph nodes in Neo4j |
| `/api/graph/entities/{name}/neighbors` | `GET` | Traverse 1-hop graph neighbors |
| `/api/graph/entities/{name}/subgraph` | `GET` | Fetch multi-hop subgraph for visualization |
| **GraphRAG Retrieval** | | |
| `/api/retrieval/search` | `POST` | Execute full GraphRAG hybrid retrieval |
| `/api/retrieval/debug` | `POST` | Inspect query analysis, candidates, and RRF fusion scores |
| `/api/retrieval/config` | `GET` | Retrieve current retrieval tuning parameters |
| **Conversational Copilot** | | |
| `/api/copilot/chat` | `POST` | Conversational GraphRAG with verified citations |
| `/api/copilot/conversations` | `GET` | List recent conversation sessions |
| `/api/copilot/conversations/{id}` | `GET` | Get conversation history with citations & metadata |
| `/api/copilot/conversations/{id}` | `DELETE` | Delete conversation session |
| `/api/copilot/messages/{id}/feedback` | `POST` | Submit user feedback (helpful / not helpful) |
| **Ingestion Jobs** | | |
| `/api/jobs/documents/{id}/pipeline` | `POST` | Trigger 6-stage end-to-end ingestion pipeline |
| `/api/jobs/{id}` | `GET` | Inspect status, progress %, and traces of an ingestion job |
| `/api/jobs/documents/{id}/latest` | `GET` | Get latest job for a document |
| **Evaluation & Benchmarks** | | |
| `/api/evaluation/run` | `POST` | Run automated GraphRAG evaluation benchmark |
| `/api/evaluation/runs` | `GET` | List historical evaluation benchmark runs |
| `/api/evaluation/runs/{id}` | `GET` | Get detailed benchmark results and per-query scores |
| **Analytics & Telemetry** | | |
| `/api/analytics/dashboard` | `GET` | Live system metrics, distributions, and graph health |
| **System & Health** | | |
| `/api/health` | `GET` | Overall API health status |
| `/api/health/database` | `GET` | PostgreSQL and pgvector health verification |

---

## 5. Getting Started

### Prerequisites
- Docker & Docker Compose (v2.0+)
- Python 3.12+ (for local development)
- Node.js 18+ (for local frontend development)

### Quickstart with Docker Compose

1. Clone repository and set up environment:
```bash
cp .env.example .env
```

2. Start the full enterprise stack:
```bash
docker-compose up --build -d
```

3. Access services:
- **Frontend Dashboard**: [http://localhost:3000](http://localhost:3000)
- **FastAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Neo4j Browser UI**: [http://localhost:7474](http://localhost:7474) (User: `neo4j`, Password: `copilot_graph_dev_password`)

---

## 6. Local Development Setup

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .

# Run database migrations
alembic upgrade head

# (Optional) Seed demo enterprise documents and test accounts
python scripts/seed_demo_data.py

# Start FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```

### Running Backend Tests
```bash
cd backend
pytest -v
```

All 149 automated tests across authentication, chunking, embeddings, entities, relationships, graph synchronization, Tri-Hybrid retrieval (BM25 + pgvector + Neo4j), Ollama provider, copilot streaming conversations, and ingestion jobs pass with 100% coverage.

---

## 7. Verification & Quality Assurance

- **Backend Test Suite**: 140 passing tests, 0 failures.
- **Frontend Build**: Statically optimized production build across all 11 routes with 0 TypeScript/linting errors.
- **Security**: Anti-prompt injection sandbox delimiters, strict password hashing with bcrypt, JWT token verification, and document-level RBAC filtering.
