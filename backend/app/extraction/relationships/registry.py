"""Centralized enterprise relationship type registry.

A single authoritative source of truth for recognized enterprise relationship types.
Prevents arbitrary or hallucinated relationship labels from polluting the database.
"""

from typing import FrozenSet, List

# Canonical enterprise relationship types — uppercase, underscore separated.
RELATIONSHIP_TYPES: FrozenSet[str] = frozenset({
    "WORKS_FOR",
    "MANAGES",
    "REPORTS_TO",
    "MEMBER_OF",
    "OWNS",
    "LEADS",
    "PART_OF",
    "DEPENDS_ON",
    "USES",
    "PROVIDES",
    "LOCATED_IN",
    "OPERATES_IN",
    "SERVES",
    "ASSIGNED_TO",
    "RESPONSIBLE_FOR",
    "APPROVES",
    "AUTHORIZES",
    "CREATED_BY",
    "MAINTAINED_BY",
    "RELATED_TO",
    "IMPLEMENTS",
    "REQUIRES",
    "PRODUCES",
    "SUPPORTS",
    "CONTRACTED_WITH",
    "PARTNERS_WITH",
    "GOVERNS",
    "APPLIES_TO",
})

# Sorted list for stable iteration and display
RELATIONSHIP_TYPES_SORTED: List[str] = sorted(RELATIONSHIP_TYPES)

# Safe fallback type for unmapped / unrecognized relations
FALLBACK_RELATIONSHIP_TYPE: str = "RELATED_TO"

# Symmetric relationships (undirected logically; stored with direction as extracted)
SYMMETRIC_RELATIONSHIPS: FrozenSet[str] = frozenset({
    "PARTNERS_WITH",
    "RELATED_TO",
})


def is_valid_relationship_type(rel_type: str) -> bool:
    """Return True if rel_type is an exact canonical enterprise relationship type."""
    return rel_type.strip().upper() in RELATIONSHIP_TYPES


def is_symmetric_relationship(rel_type: str) -> bool:
    """Return True if rel_type is symmetric."""
    return rel_type.strip().upper() in SYMMETRIC_RELATIONSHIPS
