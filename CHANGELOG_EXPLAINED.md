# Enterprise Knowledge Copilot — Architecture & Interview Cheatsheet

This document provides a concise architectural guide and interview cheatsheet for the **Enterprise Knowledge Graph RAG Copilot**, explaining key technical choices in simple, direct language.

---

## 1. Project Overview & Business Value

| Property | Details |
|---|---|
| **Core Concept** | Enterprise-grade Knowledge Graph RAG (GraphRAG) Copilot combining dense vector embeddings with multi-hop relational graph reasoning. |
| **Backend Stack** | Python, FastAPI, SQLAlchemy (async), LangChain/LlamaIndex abstractions |
| **Vector Database** | PostgreSQL with `pgvector` for dense semantic vector search (cosine distance) |
| **Graph Database** | Neo4j for multi-hop entity-relationship traversal (Cypher queries) |
| **Keyword Search** | BM25 Full-Text Search for exact terminology and code/ID matching |
| **Local LLM** | Ollama container integration for zero-cost, private offline inference |
| **Frontend** | Next.js 14 (App Router), TypeScript, Tailwind CSS, SSE real-time token streaming |

---

## 2. Key Architectural Decisions

### 1. Why Tri-Hybrid Retrieval (BM25 + pgvector + Neo4j)?
- **Dense Vector Search (`pgvector`):** Excels at conceptual semantic similarity ("What are our remote work guidelines?"), but struggles with exact entity codes, employee IDs, and specific policy numbers.
- **Keyword Search (BM25):** Excels at finding exact alphanumeric matches and domain-specific abbreviations.
- **Knowledge Graph (Neo4j):** Solves the classic "isolated chunk" problem of standard vector RAG. It traverses multi-hop relationships: e.g., `Employee` -> `Reports To` -> `Manager` -> `Approves` -> `Budget`.
- **Reciprocal Rank Fusion (RRF):** Merges the ranked candidate results from all three retrieval engines using formula:
  $$RRF(d) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
  ensuring the most comprehensively grounded context is fed into the LLM.

### 2. Zero-Hallucination Verified Citations
- Responses include a real-time slide-out **Provenance Drawer** linking generated claims directly to exact source document chunks and graph entity paths.

---

## 3. Technical Interview Cheatsheet

### Q: What is the difference between standard Vector RAG and GraphRAG?
> **Answer:** "Standard Vector RAG slices documents into chunks and computes embedding similarity. While effective for semantic lookup, it completely misses structural relationships spanning across documents (e.g. supply chain hierarchies or regulatory dependencies). GraphRAG extracts entities and relationships into Neo4j, allowing the LLM to perform multi-hop graph traversals alongside dense vector similarity."

### Q: Why did you incorporate Ollama alongside cloud LLM providers?
> **Answer:** "Enterprise clients frequently deal with confidential intellectual property, proprietary financial sheets, and patient or employee PII. By supporting an Ollama local service container, the copilot can operate in a strictly air-gapped, zero-cost private environment without transmitting proprietary prompts over third-party APIs."
