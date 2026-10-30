"""Pydantic schemas for Knowledge Graph nodes, edges, subgraphs, and sync operations."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    """Represents a node in the enterprise Knowledge Graph (typically an Entity)."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique stable entity UUID")
    label: str = Field("Entity", description="Primary Neo4j label")
    entity_type: str = Field("OTHER", description="Enterprise type e.g. PERSON, ORGANIZATION")
    canonical_name: str = Field(..., description="Normalized canonical name")
    display_name: str = Field(..., description="Human-readable surface name")
    description: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Represents a directed typed relationship between two entities."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Unique relationship/edge UUID")
    source: str = Field(..., description="Source entity UUID")
    target: str = Field(..., description="Target entity UUID")
    type: str = Field(..., description="Controlled relationship type, e.g. WORKS_FOR")
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    evidence_text: Optional[str] = None
    document_id: Optional[str] = None
    chunk_id: Optional[str] = None
    source_start_char: Optional[int] = None
    source_end_char: Optional[int] = None
    target_start_char: Optional[int] = None
    target_end_char: Optional[int] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class SubgraphResponse(BaseModel):
    """A subgraph containing a bounded set of nodes and edges for visualization and GraphRAG."""

    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    truncated: bool = Field(False, description="True if results were limited by safety bounds")
    total_nodes: int = 0
    total_edges: int = 0


class DocumentProvenance(BaseModel):
    """Document provenance associated with an entity in the graph."""
    document_id: str
    filename: str
    mention_count: int = 0


class GraphEntityDetailResponse(BaseModel):
    """Full detail of a graph entity with incoming/outgoing edges and document references."""

    entity: GraphNode
    incoming: List[GraphEdge] = Field(default_factory=list)
    outgoing: List[GraphEdge] = Field(default_factory=list)
    documents: List[DocumentProvenance] = Field(default_factory=list)
    total_incoming: int = 0
    total_outgoing: int = 0


class GraphNeighborsResponse(BaseModel):
    """Neighbors of an entity up to depth N."""

    entity_id: str
    depth: int = 1
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


class GraphSyncRequest(BaseModel):
    """Payload to trigger synchronization from PostgreSQL to Neo4j."""

    document_id: Optional[str] = Field(None, description="Optional document ID for scoped sync")
    force: bool = Field(False, description="If True, re-sync all records regardless of timestamps")


class GraphSyncResponse(BaseModel):
    """Statistics returned upon completing graph synchronization."""

    documents_synced: int = 0
    chunks_synced: int = 0
    entities_synced: int = 0
    mentions_synced: int = 0
    relationships_synced: int = 0
    errors: int = 0
    duration_ms: float = 0.0
    message: str = ""


class GraphHealthResponse(BaseModel):
    """Health status of the Neo4j graph database."""

    status: str = Field(..., examples=["healthy", "unhealthy"])
    database: str = Field("neo4j")
    connected: bool = True
    node_count: Optional[int] = None
    relationship_count: Optional[int] = None
    error: Optional[str] = None
