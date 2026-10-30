"""Deterministic relationship type normalization.

Maps common variants, inflected forms, and natural language phrases
to the controlled enterprise relationship vocabulary.
"""

import re
import unicodedata
from typing import Dict

from app.extraction.relationships.registry import (
    FALLBACK_RELATIONSHIP_TYPE,
    RELATIONSHIP_TYPES,
)

# Common enterprise surface phrases mapped to canonical relationship types
_RELATIONSHIP_ALIASES: Dict[str, str] = {
    # Employment / Organization
    "works for": "WORKS_FOR",
    "works_for": "WORKS_FOR",
    "works-for": "WORKS_FOR",
    "employed by": "WORKS_FOR",
    "employed at": "WORKS_FOR",
    "employee of": "WORKS_FOR",
    "staff at": "WORKS_FOR",
    "works at": "WORKS_FOR",
    # Management & Reporting
    "manages": "MANAGES",
    "managed by": "REPORTS_TO",
    "manager of": "MANAGES",
    "supervises": "MANAGES",
    "oversees": "MANAGES",
    "directs": "MANAGES",
    "reports to": "REPORTS_TO",
    "reports_to": "REPORTS_TO",
    "reports-to": "REPORTS_TO",
    "reporting to": "REPORTS_TO",
    "subordinate to": "REPORTS_TO",
    # Membership & Affiliation
    "member of": "MEMBER_OF",
    "member_of": "MEMBER_OF",
    "member-of": "MEMBER_OF",
    "belongs to": "MEMBER_OF",
    "part of team": "MEMBER_OF",
    # Ownership & Leadership
    "owns": "OWNS",
    "owned by": "OWNS",
    "owner of": "OWNS",
    "leads": "LEADS",
    "led by": "LEADS",
    "leader of": "LEADS",
    "head of": "LEADS",
    # Structure & Hierarchy
    "part of": "PART_OF",
    "part_of": "PART_OF",
    "part-of": "PART_OF",
    "component of": "PART_OF",
    "division of": "PART_OF",
    "subset of": "PART_OF",
    # Dependency & Tech
    "depends on": "DEPENDS_ON",
    "depends_on": "DEPENDS_ON",
    "depends-on": "DEPENDS_ON",
    "relies on": "DEPENDS_ON",
    "requires": "REQUIRES",
    "prerequisite of": "REQUIRES",
    "uses": "USES",
    "utilizes": "USES",
    "built with": "USES",
    "powered by": "USES",
    "runs on": "USES",
    "implements": "IMPLEMENTS",
    "implemented by": "IMPLEMENTS",
    # Offerings & Delivery
    "provides": "PROVIDES",
    "supplies": "PROVIDES",
    "delivers": "PROVIDES",
    "produces": "PRODUCES",
    "generates": "PRODUCES",
    "manufactures": "PRODUCES",
    "serves": "SERVES",
    "serves clients in": "SERVES",
    # Geography & Location
    "located in": "LOCATED_IN",
    "located_in": "LOCATED_IN",
    "located-in": "LOCATED_IN",
    "based in": "LOCATED_IN",
    "situated in": "LOCATED_IN",
    "headquartered in": "LOCATED_IN",
    "operates in": "OPERATES_IN",
    "operates_in": "OPERATES_IN",
    "active in": "OPERATES_IN",
    # Responsibility & Assignment
    "assigned to": "ASSIGNED_TO",
    "assigned_to": "ASSIGNED_TO",
    "responsible for": "RESPONSIBLE_FOR",
    "responsible_for": "RESPONSIBLE_FOR",
    "is responsible for": "RESPONSIBLE_FOR",
    "is responsible for managing": "MANAGES",
    "accountable for": "RESPONSIBLE_FOR",
    # Approvals & Governance
    "approves": "APPROVES",
    "approved by": "APPROVES",
    "authorizes": "AUTHORIZES",
    "authorized by": "AUTHORIZES",
    "governs": "GOVERNS",
    "governed by": "GOVERNS",
    "applies to": "APPLIES_TO",
    "applies_to": "APPLIES_TO",
    # Authorship & Maintenance
    "created by": "CREATED_BY",
    "created_by": "CREATED_BY",
    "authored by": "CREATED_BY",
    "written by": "CREATED_BY",
    "maintained by": "MAINTAINED_BY",
    "maintained_by": "MAINTAINED_BY",
    "supported by": "SUPPORTS",
    "supports": "SUPPORTS",
    # Commercial & Partnerships
    "contracted with": "CONTRACTED_WITH",
    "contracted_with": "CONTRACTED_WITH",
    "partners with": "PARTNERS_WITH",
    "partners_with": "PARTNERS_WITH",
    "partner of": "PARTNERS_WITH",
    "in partnership with": "PARTNERS_WITH",
    # Fallback / General
    "related to": "RELATED_TO",
    "related_to": "RELATED_TO",
    "associated with": "RELATED_TO",
    "connected to": "RELATED_TO",
    "linked to": "RELATED_TO",
}


def normalize_relationship_type(raw_type: str) -> str:
    """Normalize a raw or provider-generated relationship type string.

    Steps:
    1. Unicode NFKC normalization and whitespace strip.
    2. Check direct uppercase match in RELATIONSHIP_TYPES.
    3. Normalize spaces/hyphens to underscore or single space, check alias map.
    4. If uppercase form is in RELATIONSHIP_TYPES, use it.
    5. Fallback policy: Map unknown non-empty relations to FALLBACK_RELATIONSHIP_TYPE (RELATED_TO).

    Returns:
        Canonical uppercase enterprise relationship type string.
    """
    if not raw_type or not raw_type.strip():
        return FALLBACK_RELATIONSHIP_TYPE

    cleaned = unicodedata.normalize("NFKC", raw_type).strip()

    # Exact canonical check first
    upper_cleaned = cleaned.upper().replace("-", "_").replace(" ", "_")
    if upper_cleaned in RELATIONSHIP_TYPES:
        return upper_cleaned

    # Lowercase lookup in alias table
    lower_normalized = re.sub(r"\s+", " ", cleaned.lower()).replace("-", " ")
    if lower_normalized in _RELATIONSHIP_ALIASES:
        return _RELATIONSHIP_ALIASES[lower_normalized]

    # Try underscore variant in alias table
    underscore_variant = lower_normalized.replace(" ", "_")
    if underscore_variant in _RELATIONSHIP_ALIASES:
        return _RELATIONSHIP_ALIASES[underscore_variant]

    # If already a valid canonical identifier
    candidate = re.sub(r"[^A-Za-z0-9_]+", "_", cleaned).upper().strip("_")
    if candidate in RELATIONSHIP_TYPES:
        return candidate

    # Documented policy: map unrecognized relationship to controlled fallback
    return FALLBACK_RELATIONSHIP_TYPE
