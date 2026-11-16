"""In-memory structured mock knowledge graph store.

Provides fallback graph topologies and query resolution when Neo4j is offline
or when MOCK_NEO4J=True is configured for local development without Docker.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MOCK_ENTITIES: List[Dict[str, Any]] = [
    {
        "id": "ent-copilot-001",
        "canonical_name": "enterprise knowledge copilot",
        "display_name": "Enterprise Knowledge Copilot",
        "entity_type": "SYSTEM",
        "description": "Production GraphRAG and hybrid search copilot platform.",
        "confidence": 0.98,
    },
    {
        "id": "ent-fastapi-002",
        "canonical_name": "fastapi web gateway",
        "display_name": "FastAPI Web Gateway",
        "entity_type": "SERVICE",
        "description": "Asynchronous REST API gateway with OAuth2 JWT security.",
        "confidence": 0.95,
    },
    {
        "id": "ent-neo4j-003",
        "canonical_name": "neo4j knowledge graph",
        "display_name": "Neo4j Knowledge Graph",
        "entity_type": "DATABASE",
        "description": "Graph database storing entity-relationship topology and subgraphs.",
        "confidence": 0.99,
    },
    {
        "id": "ent-postgres-004",
        "canonical_name": "postgresql persistence store",
        "display_name": "PostgreSQL Persistence Store",
        "entity_type": "DATABASE",
        "description": "Relational document and metadata storage.",
        "confidence": 0.99,
    },
    {
        "id": "ent-graphrag-005",
        "canonical_name": "hybrid graphrag engine",
        "display_name": "Hybrid GraphRAG Engine",
        "entity_type": "COMPONENT",
        "description": "Combines vector embeddings, keyword BM25, and multi-hop graph retrieval.",
        "confidence": 0.96,
    },
    {
        "id": "ent-prachi-006",
        "canonical_name": "prachi zala",
        "display_name": "Prachi Zala",
        "entity_type": "PERSON",
        "description": "Principal engineer and system architect.",
        "confidence": 1.0,
    },
]

MOCK_RELATIONSHIPS: List[Dict[str, Any]] = [
    {
        "id": "rel-001",
        "source_entity_id": "ent-fastapi-002",
        "target_entity_id": "ent-copilot-001",
        "relationship_type": "PROVIDES_INTERFACE_FOR",
        "confidence": 0.95,
        "evidence_text": "FastAPI serves as the primary ingress interface for Enterprise Knowledge Copilot.",
    },
    {
        "id": "rel-002",
        "source_entity_id": "ent-copilot-001",
        "target_entity_id": "ent-graphrag-005",
        "relationship_type": "USES_ENGINE",
        "confidence": 0.97,
        "evidence_text": "Copilot queries are routed through the hybrid GraphRAG retrieval engine.",
    },
    {
        "id": "rel-003",
        "source_entity_id": "ent-graphrag-005",
        "target_entity_id": "ent-neo4j-003",
        "relationship_type": "TRAVERSES_TOPOLOGY",
        "confidence": 0.98,
        "evidence_text": "GraphRAG traverses multi-hop entity relations in the Neo4j knowledge graph.",
    },
    {
        "id": "rel-004",
        "source_entity_id": "ent-copilot-001",
        "target_entity_id": "ent-postgres-004",
        "relationship_type": "PERSISTS_DOCUMENTS_TO",
        "confidence": 0.96,
        "evidence_text": "Parsed document chunks and audit metadata are saved to PostgreSQL.",
    },
    {
        "id": "rel-005",
        "source_entity_id": "ent-prachi-006",
        "target_entity_id": "ent-copilot-001",
        "relationship_type": "ARCHITECTED_BY",
        "confidence": 1.0,
        "evidence_text": "Enterprise Knowledge Copilot was designed and engineered by Prachi Zala.",
    },
]


class MockGraphStore:
    """In-memory query resolver emulating Neo4j Cypher queries."""

    def __init__(self) -> None:
        self.entities = list(MOCK_ENTITIES)
        self.relationships = list(MOCK_RELATIONSHIPS)
        self.entity_map = {e["id"]: e for e in self.entities}

    def execute_mock_query(
        self, query: str, parameters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Interpret and resolve Cypher queries against in-memory mock topology."""
        params = parameters or {}
        q = query.strip()

        # 1. Node count query
        if "count(n) AS node_count" in q:
            return [{"node_count": len(self.entities)}]

        # 2. Relationship count query
        if "count(r) AS rel_count" in q:
            return [{"rel_count": len(self.relationships)}]

        # 3. Search entities by query substring
        if "WHERE toLower(e.canonical_name) CONTAINS" in q or "search_entities" in q:
            search_str = (params.get("q") or "").lower()
            limit = int(params.get("limit") or 20)
            matched = [
                {"e": e}
                for e in self.entities
                if not search_str
                or search_str in e["canonical_name"].lower()
                or search_str in e["display_name"].lower()
            ]
            return matched[:limit] if matched else [{"e": e} for e in self.entities[:limit]]

        # 4. Get specific entity by ID
        if "MATCH (e:Entity {id: $id})" in q or "MATCH (e:Entity {id: $entity_id})" in q:
            target_id = params.get("id") or params.get("entity_id")
            if target_id in self.entity_map:
                return [{"e": self.entity_map[target_id]}]
            # Fallback: return first entity if requested entity not found
            return [{"e": self.entities[0]}] if self.entities else []

        # 5. Outgoing edges: MATCH (s:Entity {id: $id})-[r]->(t:Entity)
        if "MATCH (s:Entity {id: $id})-[r]->(t:Entity)" in q:
            eid = params.get("id")
            records = []
            for rel in self.relationships:
                if rel["source_entity_id"] == eid:
                    target_entity = self.entity_map.get(rel["target_entity_id"], self.entities[0])
                    records.append({
                        "r": rel,
                        "t": target_entity,
                        "rel_type": rel["relationship_type"],
                    })
            # If no direct edges found, fabricate a sample relationship to copilot
            if not records and eid and self.entities:
                records.append({
                    "r": self.relationships[0],
                    "t": self.entities[0],
                    "rel_type": self.relationships[0]["relationship_type"],
                })
            return records

        # 6. Incoming edges: MATCH (s:Entity)-[r]->(t:Entity {id: $id})
        if "MATCH (s:Entity)-[r]->(t:Entity {id: $id})" in q:
            eid = params.get("id")
            records = []
            for rel in self.relationships:
                if rel["target_entity_id"] == eid:
                    src_entity = self.entity_map.get(rel["source_entity_id"], self.entities[0])
                    records.append({
                        "r": rel,
                        "s": src_entity,
                        "rel_type": rel["relationship_type"],
                    })
            return records

        # 7. Document provenance / mentions: MATCH (e:Entity {id: $id})-[:MENTIONED_IN]->
        if "MENTIONED_IN" in q:
            return [{
                "document_id": "doc-sample-001",
                "title": "Architecture Overview & GraphRAG Specification",
                "chunk_id": "chunk-sample-001",
                "frequency": 3,
            }]

        # 8. Neighbors & Subgraphs: MATCH path = (start:Entity ...
        if "subgraph" in q.lower() or "neighbors" in q.lower() or "RETURN nodes, relationships" in q or "RETURN all_nodes" in q or "RETURN doc_entities" in q:
            return [{
                "nodes": self.entities,
                "relationships": self.relationships,
                "node_list": self.entities,
                "rel_list": self.relationships,
            }]

        # 9. Default catch-all for schema statements or unhandled queries
        logger.debug("MockGraphStore received query: %s", q[:80])
        return []


mock_store = MockGraphStore()
