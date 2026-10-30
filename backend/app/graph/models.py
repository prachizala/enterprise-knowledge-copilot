"""Internal graph entity and relationship data models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class GraphNodeModel:
    """Internal model for an Entity node in Neo4j."""

    id: str
    entity_type: str
    canonical_name: str
    display_name: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphEdgeModel:
    """Internal model for an EntityRelationship edge in Neo4j."""

    id: str
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    confidence: float = 1.0
    evidence_text: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_start_char: Optional[int] = None
    source_end_char: Optional[int] = None
    target_start_char: Optional[int] = None
    target_end_char: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    properties: Dict[str, Any] = field(default_factory=dict)
