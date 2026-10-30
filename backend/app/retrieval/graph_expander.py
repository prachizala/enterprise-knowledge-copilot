"""Multi-hop Graph Expansion: executes controlled multi-hop path traversal in Neo4j."""

import logging
from typing import List, Optional, Set
from app.graph.client import get_neo4j_client
from app.graph.queries import ALLOWED_GRAPH_RELATIONSHIP_TYPES
from app.retrieval.schemas import GraphPath, LinkedEntity

logger = logging.getLogger(__name__)


class GraphExpander:
    """Discovers structured multi-hop paths connecting query entities across the Knowledge Graph."""

    @staticmethod
    async def expand_paths(
        linked_entities: List[LinkedEntity],
        depth: int = 2,
        max_paths: int = 20,
        allowed_document_ids: Optional[Set[str]] = None,
    ) -> List[GraphPath]:
        """Traverse 2-hop or 3-hop paths starting from linked entities and return structured reasoning chains."""
        if not linked_entities:
            return []

        client = get_neo4j_client()
        if not client.is_connected:
            connected = await client.connect()
            if not connected:
                return []

        safe_depth = max(1, min(depth, 3))
        entity_ids = [le.entity_id for le in linked_entities]

        cypher = f"""
        MATCH path = (start:Entity)-[r*1..{safe_depth}]->(target:Entity)
        WHERE start.id IN $entity_ids
          AND ALL(rel IN relationships(path) WHERE type(rel) <> 'MENTIONED_IN' AND type(rel) <> 'PART_OF')
        RETURN path, nodes(path) AS path_nodes, relationships(path) AS path_rels
        LIMIT $max_paths
        """

        try:
            records = await client.execute_query(
                cypher,
                {"entity_ids": entity_ids, "max_paths": max_paths * 2},
            )
        except Exception as exc:
            logger.warning("Multi-hop graph expansion error: %s", exc)
            records = []

        discovered_paths: List[GraphPath] = []
        seen_signatures = set()

        for rec in records:
            p_nodes = rec.get("path_nodes", []) or []
            p_rels = rec.get("path_rels", []) or []

            if not p_nodes or not p_rels:
                continue

            # Build text representation and collect provenance
            nodes_summary = []
            rels_summary = []
            evidences = []
            chunk_ids = []
            doc_ids = []
            confidence_product = 1.0
            is_authorized = True

            for n in p_nodes:
                name = n.get("display_name") or n.get("canonical_name") or n.get("id")
                etype = n.get("entity_type", "OTHER")
                nodes_summary.append({"id": n.get("id"), "name": name, "type": etype})

            for r in p_rels:
                rtype = r.get("relationship_type") or r.get("type", "RELATED_TO")
                ev_text = r.get("evidence_text")
                doc_id = r.get("document_id")
                chunk_id = r.get("chunk_id")
                conf = float(r.get("confidence", 1.0))

                # Enforce RBAC filtering on path provenance
                if allowed_document_ids is not None and doc_id and doc_id not in allowed_document_ids:
                    is_authorized = False
                    break

                rels_summary.append({
                    "type": rtype,
                    "confidence": conf,
                    "document_id": doc_id,
                    "chunk_id": chunk_id,
                })
                if ev_text:
                    evidences.append(ev_text)
                if doc_id:
                    doc_ids.append(doc_id)
                if chunk_id:
                    chunk_ids.append(chunk_id)

                confidence_product *= conf

            if not is_authorized or not rels_summary:
                continue

            # Format readable path string: NodeA (TYPE) -[:REL]-> NodeB (TYPE)
            path_tokens = []
            for i, n in enumerate(nodes_summary):
                path_tokens.append(f"{n['name']} ({n['type']})")
                if i < len(rels_summary):
                    path_tokens.append(f"-[:{rels_summary[i]['type']}]->")

            formatted_path = " ".join(path_tokens)
            if formatted_path in seen_signatures:
                continue
            seen_signatures.add(formatted_path)

            discovered_paths.append(
                GraphPath(
                    nodes=nodes_summary,
                    relationships=rels_summary,
                    hops=len(rels_summary),
                    formatted_path=formatted_path,
                    evidence_texts=evidences,
                    source_chunk_ids=chunk_ids,
                    document_ids=doc_ids,
                    confidence=round(confidence_product, 3),
                )
            )
            if len(discovered_paths) >= max_paths:
                break

        return discovered_paths
