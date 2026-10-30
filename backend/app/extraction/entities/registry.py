"""Entity type registry for the extraction pipeline.

A single authoritative source of truth for recognized entity types.
New types should be added here only; downstream code depends on this set.
"""

from typing import FrozenSet

# Canonical entity type identifiers — uppercase, no spaces.
ENTITY_TYPES: FrozenSet[str] = frozenset({
    "PERSON",
    "ORGANIZATION",
    "DEPARTMENT",
    "PROJECT",
    "PRODUCT",
    "LOCATION",
    "POLICY",
    "TECHNOLOGY",
    "DATE",
    "MONEY",
    "EMAIL",
    "PHONE",
    "CONTRACT",
    "ROLE",
    "OTHER",
})

# Sorted list for display / iteration stability
ENTITY_TYPES_SORTED: list[str] = sorted(ENTITY_TYPES)


def is_valid_entity_type(entity_type: str) -> bool:
    """Return True if *entity_type* is a recognized canonical type."""
    return entity_type.upper() in ENTITY_TYPES


def normalize_entity_type(entity_type: str) -> str:
    """Return canonical uppercase entity type or 'OTHER' if unrecognized."""
    normalized = entity_type.strip().upper()
    return normalized if normalized in ENTITY_TYPES else "OTHER"
