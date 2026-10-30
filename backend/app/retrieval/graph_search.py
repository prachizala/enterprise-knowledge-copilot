"""Knowledge Graph search service executing entity and relationship retrieval."""

import logging
from typing import List, Optional, Set
from app.graph.client import get_neo4j_client
from app.retrieval.schemas import GraphCandidate, LinkedEntity

logger = logging.getLogger(__name__)


class GraphSearchService:
    """Retrieves entities, direct relationships, and grounded chunk references from Neo4j."""

    @staticmethod
    async def search_entities(
        linked_entities: List[LinkedEntity],
        allowed_document_ids: Optional[Set[str]] = None,
        max_edges_per_entity: int = 25,
    ) -> List[GraphCandidate]:
        """Query Neo4j for 1-hop relationships and grounded chunk IDs for linked entities."""
        if not linked_entities:
            return []

        client = get_neo4j_client()
        if not client.is_connected:
            connected = await client.connect()
            if not connected:
                logger.warning("Neo4j is not connected. Skipping graph candidate search.")
                return []

        candidates: List[GraphCandidate] = []

        for le in linked_entities:
            cypher = """
            MATCH (e:Entity {id: $entity_id})
            OPTIONAL MATCH (e)-[r]->(target:Entity)
            WHERE type(r) <> 'MENTIONED_IN' AND type(r) <> 'PART_OF'
            RETURN e, type(r) AS rel_type, r, target
            LIMIT $limit
            """
            try:
                records = await client.execute_query(
                    cypher,
                    {"entity_id": le.entity_id, "limit": max_edges_per_entity},
                )
            except Exception as exc:
                logger.warning("Graph entity search error for %s: %s", le.entity_id, exc)
                records = []

            direct_rels = []
            chunk_ids = set()
            doc_ids = set()

            for rec in records:
                rel = rec.get("r")
                target = rec.get("target")
                rel_type = rec.get("rel_type")
                if rel and target and rel_type:
                    doc_id = rel.get("document_id")
                    chunk_id = rel.get("chunk_id")

                    # Apply document-level access filter if specified
                    if allowed_document_ids is not None and doc_id and doc_id not in allowed_document_ids:
                        continue

                    if chunk_id:
                        chunk_ids.add(chunk_id)
                    if doc_id:
                        doc_ids.add(doc_id)

                    direct_rels.append({
                        "relationship_type": rel_type,
                        "target_id": target.get("id"),
                        "target_name": target.get("display_name") or target.get("canonical_name"),
                        "target_type": target.get("entity_type"),
                        "confidence": float(rel.get("confidence", 1.0)),
                        "evidence_text": rel.get("evidence_text"),
                        "document_id": doc_id,
                        "chunk_id": chunk_id,
                    })

            # Also query mentions for source chunks
            mention_cypher = """
            MATCH (e:Entity {id: $entity_id})-[:MENTIONED_IN]->(c:Chunk)
            RETURN c.id AS chunk_id, c.document_id AS document_id
            LIMIT 20
            """
            try:
                mention_records = await client.execute_query(
                    mention_cypher,
                    {"entity_id": le.entity_id},
                )
                for mr in mention_records:
                    cid = mr.get("chunk_id")
                    did = mr.get("document_id")
                    if allowed_document_ids is not None and did and did not in allowed_document_ids:
                        continue
                    if cid:
                        chunk_ids.add(cid)
                    if did:
                        doc_ids.add(did)
            except Exception as exc:
                logger.debug("Mention query error for %s: %s", le.entity_id, exc)

            candidates.append(
                GraphCandidate(
                    entity_id=le.entity_id,
                    canonical_name=le.canonical_name,
                    entity_type=le.entity_type,
                    direct_relationships=direct_rels,
                    degree=len(direct_rels),
                    relevance_score=le.confidence,
                    associated_chunk_ids=list(chunk_ids),
                    associated_document_ids=list(doc_ids),
                )
            )

        return candidates
