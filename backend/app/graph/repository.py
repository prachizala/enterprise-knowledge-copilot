"""Neo4j graph query repository: encapsulating Cypher queries, topology traversals, and subgraphs."""

import logging
from typing import Any, Dict, List, Optional

from app.graph.client import Neo4jClient, get_neo4j_client
from app.graph.queries import SCHEMA_STATEMENTS, sanitize_relationship_type
from app.graph.schemas import (
    DocumentProvenance,
    GraphEdge,
    GraphEntityDetailResponse,
    GraphNeighborsResponse,
    GraphNode,
    SubgraphResponse,
)

logger = logging.getLogger(__name__)


class GraphRepository:
    """Repository executing parameterized Cypher queries for the Knowledge Graph."""

    def __init__(self, client: Optional[Neo4jClient] = None) -> None:
        self._custom_client = client

    @property
    def _client(self) -> Neo4jClient:
        return self._custom_client or get_neo4j_client()

    async def init_schema(self) -> None:
        """Create constraints and indexes in Neo4j idempotently."""
        for stmt in SCHEMA_STATEMENTS:
            try:
                await self._client.execute_query(stmt)
            except Exception as exc:
                logger.warning("Schema initialization statement failed (%s): %s", exc, stmt.strip())

    async def search_entities(self, query: str, limit: int = 20) -> List[GraphNode]:
        """Search canonical entities by substring match in canonical_name or display_name."""
        cypher = """
        MATCH (e:Entity)
        WHERE toLower(e.canonical_name) CONTAINS toLower($q)
           OR toLower(e.display_name) CONTAINS toLower($q)
        RETURN e
        ORDER BY size(e.canonical_name) ASC
        LIMIT $limit
        """
        records = await self._client.execute_query(cypher, {"q": query, "limit": limit})
        nodes: List[GraphNode] = []
        for r in records:
            e_data = r.get("e", {})
            nodes.append(GraphNode(
                id=e_data.get("id", ""),
                label="Entity",
                entity_type=e_data.get("entity_type", "OTHER"),
                canonical_name=e_data.get("canonical_name", ""),
                display_name=e_data.get("display_name", ""),
                description=e_data.get("description"),
                properties=e_data,
            ))
        return nodes

    async def get_entity(self, entity_id: str) -> Optional[GraphNode]:
        """Retrieve a single entity node by UUID."""
        cypher = "MATCH (e:Entity {id: $id}) RETURN e"
        records = await self._client.execute_query(cypher, {"id": entity_id})
        if not records:
            return None
        e_data = records[0].get("e", {})
        return GraphNode(
            id=e_data.get("id", ""),
            label="Entity",
            entity_type=e_data.get("entity_type", "OTHER"),
            canonical_name=e_data.get("canonical_name", ""),
            display_name=e_data.get("display_name", ""),
            description=e_data.get("description"),
            properties=e_data,
        )

    async def get_entity_detail(self, entity_id: str) -> Optional[GraphEntityDetailResponse]:
        """Retrieve detailed entity information including incoming/outgoing edges and provenance."""
        entity = await self.get_entity(entity_id)
        if entity is None:
            return None

        # Outgoing edges
        out_cypher = """
        MATCH (s:Entity {id: $id})-[r]->(t:Entity)
        WHERE type(r) <> 'MENTIONED_IN' AND type(r) <> 'PART_OF'
        RETURN r, t, type(r) AS rel_type
        """
        out_records = await self._client.execute_query(out_cypher, {"id": entity_id})
        outgoing: List[GraphEdge] = []
        for r in out_records:
            rel = r.get("r", {})
            t = r.get("t", {})
            outgoing.append(GraphEdge(
                id=rel.get("id") or rel.get("relationship_id") or f"{entity_id}_{t.get('id')}",
                source=entity_id,
                target=t.get("id", ""),
                type=r.get("rel_type", "RELATED_TO"),
                confidence=float(rel.get("confidence", 1.0)),
                evidence_text=rel.get("evidence_text"),
                document_id=rel.get("document_id"),
                chunk_id=rel.get("chunk_id"),
                source_start_char=rel.get("source_start_char"),
                source_end_char=rel.get("source_end_char"),
                target_start_char=rel.get("target_start_char"),
                target_end_char=rel.get("target_end_char"),
                properties=rel,
            ))

        # Incoming edges
        in_cypher = """
        MATCH (s:Entity)-[r]->(t:Entity {id: $id})
        WHERE type(r) <> 'MENTIONED_IN' AND type(r) <> 'PART_OF'
        RETURN s, r, type(r) AS rel_type
        """
        in_records = await self._client.execute_query(in_cypher, {"id": entity_id})
        incoming: List[GraphEdge] = []
        for r in in_records:
            s = r.get("s", {})
            rel = r.get("r", {})
            incoming.append(GraphEdge(
                id=rel.get("id") or rel.get("relationship_id") or f"{s.get('id')}_{entity_id}",
                source=s.get("id", ""),
                target=entity_id,
                type=r.get("rel_type", "RELATED_TO"),
                confidence=float(rel.get("confidence", 1.0)),
                evidence_text=rel.get("evidence_text"),
                document_id=rel.get("document_id"),
                chunk_id=rel.get("chunk_id"),
                source_start_char=rel.get("source_start_char"),
                source_end_char=rel.get("source_end_char"),
                target_start_char=rel.get("target_start_char"),
                target_end_char=rel.get("target_end_char"),
                properties=rel,
            ))

        # Provenance documents via MENTIONED_IN -> Chunk -> PART_OF -> Document
        doc_cypher = """
        MATCH (e:Entity {id: $id})-[:MENTIONED_IN]->(c:Chunk)-[:PART_OF]->(d:Document)
        RETURN d.id AS doc_id, d.filename AS filename, count(c) AS mention_count
        ORDER BY mention_count DESC
        """
        doc_records = await self._client.execute_query(doc_cypher, {"id": entity_id})
        docs: List[DocumentProvenance] = [
            DocumentProvenance(
                document_id=r.get("doc_id", ""),
                filename=r.get("filename", "Unknown Document"),
                mention_count=r.get("mention_count", 0),
            )
            for r in doc_records
        ]

        return GraphEntityDetailResponse(
            entity=entity,
            incoming=incoming,
            outgoing=outgoing,
            documents=docs,
            total_incoming=len(incoming),
            total_outgoing=len(outgoing),
        )

    async def get_entity_neighbors(
        self,
        entity_id: str,
        depth: int = 1,
        relationship_type: Optional[str] = None,
        limit: int = 50,
    ) -> GraphNeighborsResponse:
        """Retrieve 1-hop or N-hop neighbors of an entity."""
        safe_depth = max(1, min(depth, 3))
        type_filter = ""
        if relationship_type:
            safe_type = sanitize_relationship_type(relationship_type)
            type_filter = f":{safe_type}"

        cypher = f"""
        MATCH path = (e:Entity {{id: $id}})-[r{type_filter}*1..{safe_depth}]-(neighbor:Entity)
        WITH nodes(path) AS ns, relationships(path) AS rs
        UNWIND ns AS n
        UNWIND rs AS rel
        RETURN collect(DISTINCT n) AS node_list, collect(DISTINCT rel) AS rel_list
        """
        records = await self._client.execute_query(cypher, {"id": entity_id})

        nodes_map: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        if records:
            row = records[0]
            for n_data in row.get("node_list", []):
                nid = n_data.get("id")
                if nid and nid not in nodes_map:
                    nodes_map[nid] = GraphNode(
                        id=nid,
                        label="Entity",
                        entity_type=n_data.get("entity_type", "OTHER"),
                        canonical_name=n_data.get("canonical_name", ""),
                        display_name=n_data.get("display_name", ""),
                        description=n_data.get("description"),
                        properties=n_data,
                    )

            for rel_data in row.get("rel_list", []):
                # Neo4j python driver returns dict for relationships
                src = rel_data.get("source_id") or rel_data.get("source_entity_id")
                tgt = rel_data.get("target_id") or rel_data.get("target_entity_id")
                edges.append(GraphEdge(
                    id=rel_data.get("id") or rel_data.get("relationship_id") or f"{src}_{tgt}",
                    source=src or "",
                    target=tgt or "",
                    type=rel_data.get("relationship_type", "RELATED_TO"),
                    confidence=float(rel_data.get("confidence", 1.0)),
                    evidence_text=rel_data.get("evidence_text"),
                    document_id=rel_data.get("document_id"),
                    chunk_id=rel_data.get("chunk_id"),
                    properties=rel_data,
                ))

        return GraphNeighborsResponse(
            entity_id=entity_id,
            depth=safe_depth,
            nodes=list(nodes_map.values())[:limit],
            edges=edges[:limit * 2],
        )

    async def get_subgraph(
        self,
        entity_id: str,
        depth: int = 2,
        max_nodes: int = 100,
        max_relationships: int = 200,
    ) -> SubgraphResponse:
        """Extract a bounded subgraph around an entity for interactive visualization and GraphRAG."""
        safe_depth = max(1, min(depth, 3))

        cypher = f"""
        MATCH (start:Entity {{id: $id}})
        CALL apoc.path.subgraphAll(start, {{
            maxLevel: {safe_depth},
            limit: $max_nodes
        }})
        YIELD nodes, relationships
        RETURN nodes, relationships
        """

        # Fallback query if APOC is not loaded in Community edition
        cypher_fallback = f"""
        MATCH path = (start:Entity {{id: $id}})-[r*1..{safe_depth}]-(other:Entity)
        WHERE ALL(rel IN relationships(path) WHERE type(rel) <> 'MENTIONED_IN' AND type(rel) <> 'PART_OF')
        WITH nodes(path) AS path_nodes, relationships(path) AS path_rels
        UNWIND path_nodes AS n
        UNWIND path_rels AS rel
        WITH collect(DISTINCT n) AS all_nodes, collect(DISTINCT rel) AS all_rels
        RETURN all_nodes[..$max_nodes] AS nodes, all_rels[..$max_relationships] AS relationships
        """

        try:
            records = await self._client.execute_query(
                cypher_fallback,
                {"id": entity_id, "max_nodes": max_nodes, "max_relationships": max_relationships},
            )
        except Exception:
            records = []

        nodes_map: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        # Always include the start entity
        start_entity = await self.get_entity(entity_id)
        if start_entity:
            nodes_map[start_entity.id] = start_entity

        if records:
            row = records[0]
            raw_nodes = row.get("nodes", []) or []
            raw_rels = row.get("relationships", []) or []

            for n_data in raw_nodes:
                nid = n_data.get("id")
                if nid and nid not in nodes_map:
                    nodes_map[nid] = GraphNode(
                        id=nid,
                        label="Entity",
                        entity_type=n_data.get("entity_type", "OTHER"),
                        canonical_name=n_data.get("canonical_name", ""),
                        display_name=n_data.get("display_name", ""),
                        description=n_data.get("description"),
                        properties=n_data,
                    )

            for rel_data in raw_rels:
                src = rel_data.get("source_entity_id") or rel_data.get("source_id") or ""
                tgt = rel_data.get("target_entity_id") or rel_data.get("target_id") or ""
                edges.append(GraphEdge(
                    id=rel_data.get("id") or rel_data.get("relationship_id") or f"{src}_{tgt}",
                    source=src,
                    target=tgt,
                    type=rel_data.get("relationship_type", "RELATED_TO"),
                    confidence=float(rel_data.get("confidence", 1.0)),
                    evidence_text=rel_data.get("evidence_text"),
                    document_id=rel_data.get("document_id"),
                    chunk_id=rel_data.get("chunk_id"),
                    properties=rel_data,
                ))

        node_list = list(nodes_map.values())
        truncated = len(node_list) >= max_nodes or len(edges) >= max_relationships

        return SubgraphResponse(
            nodes=node_list[:max_nodes],
            edges=edges[:max_relationships],
            truncated=truncated,
            total_nodes=len(node_list),
            total_edges=len(edges),
        )

    async def get_document_subgraph(
        self,
        document_id: str,
        max_nodes: int = 100,
        max_relationships: int = 200,
    ) -> SubgraphResponse:
        """Retrieve all entities and relationships originating from a specific document."""
        cypher = """
        MATCH (d:Document {id: $doc_id})<-[:PART_OF]-(c:Chunk)<-[:MENTIONED_IN]-(e:Entity)
        WITH collect(DISTINCT e) AS doc_entities
        MATCH (s:Entity)-[r]->(t:Entity)
        WHERE r.document_id = $doc_id
           OR (s IN doc_entities AND t IN doc_entities)
        RETURN doc_entities[..$max_nodes] AS nodes, collect(DISTINCT r)[..$max_relationships] AS relationships
        """
        records = await self._client.execute_query(
            cypher,
            {"doc_id": document_id, "max_nodes": max_nodes, "max_relationships": max_relationships},
        )

        nodes_map: Dict[str, GraphNode] = {}
        edges: List[GraphEdge] = []

        if records:
            row = records[0]
            for n_data in row.get("nodes", []) or []:
                nid = n_data.get("id")
                if nid and nid not in nodes_map:
                    nodes_map[nid] = GraphNode(
                        id=nid,
                        label="Entity",
                        entity_type=n_data.get("entity_type", "OTHER"),
                        canonical_name=n_data.get("canonical_name", ""),
                        display_name=n_data.get("display_name", ""),
                        description=n_data.get("description"),
                        properties=n_data,
                    )

            for rel_data in row.get("relationships", []) or []:
                src = rel_data.get("source_entity_id") or ""
                tgt = rel_data.get("target_entity_id") or ""
                edges.append(GraphEdge(
                    id=rel_data.get("id") or rel_data.get("relationship_id") or f"{src}_{tgt}",
                    source=src,
                    target=tgt,
                    type=rel_data.get("relationship_type", "RELATED_TO"),
                    confidence=float(rel_data.get("confidence", 1.0)),
                    evidence_text=rel_data.get("evidence_text"),
                    document_id=rel_data.get("document_id"),
                    chunk_id=rel_data.get("chunk_id"),
                    properties=rel_data,
                ))

        return SubgraphResponse(
            nodes=list(nodes_map.values()),
            edges=edges,
            total_nodes=len(nodes_map),
            total_edges=len(edges),
        )


graph_repository = GraphRepository()
