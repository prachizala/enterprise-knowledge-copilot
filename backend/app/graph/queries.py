"""Cypher query templates, schema constraints, and relationship sanitization."""

import re
from typing import Dict, List, Set

from app.extraction.relationships.registry import (
    FALLBACK_RELATIONSHIP_TYPE,
    RELATIONSHIP_TYPES,
)

# Whitelist of safe Neo4j relationship types
ALLOWED_GRAPH_RELATIONSHIP_TYPES: Set[str] = set(RELATIONSHIP_TYPES) | {
    "PART_OF",
    "MENTIONED_IN",
    "RELATED_TO",
}


def sanitize_relationship_type(rel_type: str) -> str:
    """Validate and sanitize relationship type string for safe Cypher edge creation.

    Cypher requires relationship types to be static syntax (not parameters).
    This function strictly maps any input to the allowed uppercase whitelist,
    falling back to FALLBACK_RELATIONSHIP_TYPE if unknown, completely eliminating Cypher injection.
    """
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", rel_type.strip()).upper().strip("_")
    if cleaned in ALLOWED_GRAPH_RELATIONSHIP_TYPES:
        return cleaned
    return FALLBACK_RELATIONSHIP_TYPE


# ── Schema Constraints & Indexes (Neo4j 5.x) ─────────────────────────────────

SCHEMA_STATEMENTS: List[str] = [
    # Unique Constraints for stable identities
    """
    CREATE CONSTRAINT constraint_entity_id IF NOT EXISTS
    FOR (e:Entity) REQUIRE e.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT constraint_document_id IF NOT EXISTS
    FOR (d:Document) REQUIRE d.id IS UNIQUE
    """,
    """
    CREATE CONSTRAINT constraint_chunk_id IF NOT EXISTS
    FOR (c:Chunk) REQUIRE c.id IS UNIQUE
    """,
    # Lookup Indexes for performance
    """
    CREATE INDEX index_entity_canonical IF NOT EXISTS
    FOR (e:Entity) ON (e.canonical_name)
    """,
    """
    CREATE INDEX index_entity_type IF NOT EXISTS
    FOR (e:Entity) ON (e.entity_type)
    """,
    """
    CREATE INDEX index_document_filename IF NOT EXISTS
    FOR (d:Document) ON (d.filename)
    """,
    """
    CREATE INDEX index_chunk_hash IF NOT EXISTS
    FOR (c:Chunk) ON (c.content_hash)
    """,
]


# ── Synchronization Cypher Queries (Idempotent MERGE) ────────────────────────

MERGE_DOCUMENT_QUERY = """
MERGE (d:Document {id: $id})
SET d.filename = $filename,
    d.file_type = $file_type,
    d.department = $department,
    d.owner = $owner,
    d.updated_at = $updated_at
"""

MERGE_CHUNK_QUERY = """
MERGE (c:Chunk {id: $id})
SET c.document_id = $document_id,
    c.chunk_index = $chunk_index,
    c.char_count = $char_count,
    c.token_count = $token_count,
    c.section_header = $section_header,
    c.page_number = $page_number,
    c.content_hash = $content_hash,
    c.updated_at = $updated_at
WITH c
MATCH (d:Document {id: $document_id})
MERGE (c)-[:PART_OF]->(d)
"""

MERGE_ENTITY_QUERY = """
MERGE (e:Entity {id: $id})
SET e.entity_type = $entity_type,
    e.canonical_name = $canonical_name,
    e.display_name = $display_name,
    e.description = $description,
    e.updated_at = $updated_at
"""

MERGE_MENTION_QUERY = """
MATCH (e:Entity {id: $entity_id})
MATCH (c:Chunk {id: $chunk_id})
MERGE (e)-[r:MENTIONED_IN {id: $mention_id}]->(c)
SET r.mention_text = $mention_text,
    r.confidence = $confidence,
    r.start_char = $start_char,
    r.end_char = $end_char
"""


def build_merge_relationship_query(safe_rel_type: str) -> str:
    """Build parameterized MERGE query for an entity-to-entity relationship."""
    sanitized = sanitize_relationship_type(safe_rel_type)
    return f"""
    MATCH (s:Entity {{id: $source_entity_id}})
    MATCH (t:Entity {{id: $target_entity_id}})
    MERGE (s)-[r:{sanitized} {{id: $relationship_id}}]->(t)
    SET r.relationship_id = $relationship_id,
        r.relationship_type = $relationship_type,
        r.confidence = $confidence,
        r.evidence_text = $evidence_text,
        r.document_id = $document_id,
        r.chunk_id = $chunk_id,
        r.source_start_char = $source_start_char,
        r.source_end_char = $source_end_char,
        r.target_start_char = $target_start_char,
        r.target_end_char = $target_end_char,
        r.provider = $provider,
        r.model = $model,
        r.created_at = $created_at,
        r.updated_at = $updated_at
    """
