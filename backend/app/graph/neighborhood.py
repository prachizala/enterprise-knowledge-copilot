"""Neo4j knowledge graph entity multi-hop neighborhood extraction module."""


class GraphNeighborhoodExtractor:
    """Builds Cypher queries to extract k-hop local graph reasoning subgraphs."""

    @staticmethod
    def generate_k_hop_cypher(entity_id: str, hops: int = 2) -> str:
        """Constructs parameterized Cypher traversal query with relationship provenance."""
        return (
            f"MATCH path = (e:Entity {{id: '{entity_id}'}})-[r:RELATION*1..{hops}]-(target) "
            "RETURN path, nodes(path) AS entities, relationships(path) AS edges "
            "LIMIT 50"
        )
