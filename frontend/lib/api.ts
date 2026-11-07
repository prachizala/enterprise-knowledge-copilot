/**
 * API client for Enterprise Knowledge Copilot Backend.
 *
 * Provides typed methods for interacting with FastAPI endpoints:
 * - Health check & Database status
 * - Document metadata CRUD & real file uploads
 * - Text extraction trigger & content inspection
 * - Secure binary file download
 */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface HealthResponse {
  status: string;
  service: string;
  app_name: string;
  environment: string;
  version: string;
}

export interface DatabaseHealthResponse {
  status: string;
  database: string;
  error?: string;
}

export interface DocumentCreateInput {
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  department: string;
  owner: string;
  description?: string;
  version?: string;
}

export interface DocumentUpdateInput {
  filename?: string;
  original_filename?: string;
  file_type?: string;
  file_size?: number;
  department?: string;
  owner?: string;
  description?: string;
  status?: "uploaded" | "processing" | "processed" | "failed";
  version?: string;
  extraction_status?: "pending" | "processing" | "completed" | "failed";
  processing_error?: string;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  original_filename: string;
  file_type: string;
  file_size: number;
  department: string;
  owner: string;
  description?: string;
  status: "uploaded" | "processing" | "processed" | "failed";
  version: string;
  mime_type?: string | null;
  extraction_status: "pending" | "processing" | "completed" | "failed";
  extracted_text_length: number;
  total_chunks: number;
  embedding_status: "not_started" | "pending" | "processing" | "completed" | "failed";
  embedded_chunks: number;
  embedding_model?: string | null;
  entity_extraction_status: "not_started" | "processing" | "completed" | "partial" | "failed";
  entity_mention_count: number;
  unique_entity_count: number;
  relationship_extraction_status: "not_started" | "processing" | "completed" | "partial" | "failed";
  relationship_count: number;
  processing_error?: string | null;
  processed_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  total: number;
  documents: DocumentResponse[];
}

export interface DocumentContentResponse {
  document_id: string;
  text: string;
  character_count: number;
  word_count: number;
  page_count?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface DocumentChunkResponse {
  id: string;
  document_id: string;
  chunk_index: number;
  content: string;
  char_count: number;
  token_count: number;
  page_number?: number | null;
  section_header?: string | null;
  chunk_metadata?: string | null;
  metadata?: Record<string, any> | null;
  content_hash?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DocumentChunkListResponse {
  total: number;
  document_id: string;
  skip: number;
  limit: number;
  chunks: DocumentChunkResponse[];
}

/**
 * Fetch general backend health status.
 */
export async function getHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/health`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Health check failed with status: ${res.status}`);
  }
  return res.json();
}

/**
 * Fetch database connectivity status.
 */
export async function getDatabaseHealth(): Promise<DatabaseHealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/health/database`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    return {
      status: "unhealthy",
      database: "disconnected",
      error: errorData?.detail?.error || `HTTP ${res.status}`,
    };
  }
  return res.json();
}

/**
 * Upload a document file (PDF, DOCX, TXT, CSV) to the backend.
 */
export async function uploadDocument(
  formData: FormData
): Promise<DocumentResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Upload failed with status code ${res.status}`
    );
  }
  return res.json();
}

/**
 * Trigger text extraction / reprocessing on an existing document.
 */
export async function processDocument(
  documentId: string
): Promise<DocumentResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/process`,
    {
      method: "POST",
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Processing failed with status ${res.status}`
    );
  }
  return res.json();
}

/**
 * Fetch extracted text and structural metrics for a document.
 */
export async function getDocumentContent(
  documentId: string
): Promise<DocumentContentResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/content`,
    {
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to fetch content: status ${res.status}`
    );
  }
  return res.json();
}

/**
 * Get direct download URL for a document.
 */
export function getDownloadUrl(documentId: string): string {
  return `${API_BASE_URL}/api/documents/${documentId}/download`;
}

/**
 * List document metadata records with filtering and pagination.
 */
export async function listDocuments(params?: {
  department?: string;
  file_type?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<DocumentListResponse> {
  const query = new URLSearchParams();
  if (params?.department && params.department !== "All") {
    query.set("department", params.department);
  }
  if (params?.file_type && params.file_type !== "All") {
    query.set("file_type", params.file_type);
  }
  if (params?.status && params.status !== "All") {
    query.set("status", params.status);
  }
  if (params?.search) {
    query.set("search", params.search);
  }
  if (params?.skip !== undefined) {
    query.set("skip", params.skip.toString());
  }
  if (params?.limit !== undefined) {
    query.set("limit", params.limit.toString());
  }

  const qs = query.toString();
  const url = `${API_BASE_URL}/api/documents${qs ? `?${qs}` : ""}`;

  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Failed to list documents: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Fetch a single document metadata record by ID.
 */
export async function getDocument(id: string): Promise<DocumentResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Failed to get document ${id}: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Create a new document metadata record.
 */
export async function createDocument(
  doc: DocumentCreateInput
): Promise<DocumentResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(doc),
  });
  if (!res.ok) {
    throw new Error(`Failed to create document: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Partially update an existing document metadata record.
 */
export async function updateDocument(
  id: string,
  update: DocumentUpdateInput
): Promise<DocumentResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(update),
  });
  if (!res.ok) {
    throw new Error(`Failed to update document ${id}: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Delete a document metadata record by ID.
 */
export async function deleteDocument(
  id: string
): Promise<{ message: string; id: string }> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    throw new Error(`Failed to delete document ${id}: ${res.statusText}`);
  }
  return res.json();
}

/**
 * Retrieve paginated chunks for a document.
 */
export async function getDocumentChunks(
  documentId: string,
  skip = 0,
  limit = 50,
  pageNumber?: number
): Promise<DocumentChunkListResponse> {
  const params = new URLSearchParams({
    skip: skip.toString(),
    limit: limit.toString(),
  });
  if (pageNumber !== undefined) {
    params.set("page_number", pageNumber.toString());
  }
  const res = await fetch(`${API_BASE_URL}/api/documents/${documentId}/chunks?${params.toString()}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to fetch chunks (HTTP ${res.status})`
    );
  }
  return res.json();
}

/**
 * Retrieve a specific chunk by its index.
 */
export async function getDocumentChunkByIndex(
  documentId: string,
  chunkIndex: number
): Promise<DocumentChunkResponse> {
  const res = await fetch(`${API_BASE_URL}/api/documents/${documentId}/chunks/${chunkIndex}`, {
    cache: "no-store",
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to fetch chunk at index ${chunkIndex} (HTTP ${res.status})`
    );
  }
  return res.json();
}

export interface EmbeddingTaskResponse {
  document_id: string;
  status: string;
  total_chunks: number;
  embedded_chunks: number;
  model: string;
  message: string;
}

export interface DocumentEmbeddingStatusResponse {
  document_id: string;
  embedding_status: "not_started" | "pending" | "processing" | "completed" | "failed";
  total_chunks: number;
  embedded_chunks: number;
  embedding_model?: string | null;
  is_up_to_date: boolean;
  last_embedded_at?: string | null;
}

export interface VectorSearchRequest {
  query: string;
  top_k?: number;
  similarity_threshold?: number;
  document_id?: string;
  department?: string;
  file_type?: string;
}

export interface VectorSearchResultItem {
  chunk_id: string;
  document_id: string;
  document_filename: string;
  document_original_filename: string;
  department: string;
  owner: string;
  file_type: string;
  chunk_index: number;
  content: string;
  char_count: number;
  token_count: number;
  page_number?: number | null;
  section_header?: string | null;
  similarity_score: number;
  distance: number;
  model: string;
}

export interface VectorSearchResponse {
  query: string;
  total_results: number;
  top_k: number;
  results: VectorSearchResultItem[];
  search_time_ms: number;
  model: string;
}

export interface ReindexResponse {
  total_documents: number;
  processed_documents: number;
  total_chunks_embedded: number;
  skipped_chunks: number;
  failed_documents: number;
  errors: string[];
}

/**
 * Generate or refresh dense vector embeddings for all chunks of a document.
 */
export async function generateDocumentEmbeddings(
  documentId: string,
  force = false
): Promise<EmbeddingTaskResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/embeddings?force=${force}`,
    {
      method: "POST",
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to generate embeddings (HTTP ${res.status})`
    );
  }
  return res.json();
}

/**
 * Fetch detailed embedding status and chunk coverage for a document.
 */
export async function getDocumentEmbeddingStatus(
  documentId: string
): Promise<DocumentEmbeddingStatusResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/embedding-status`,
    {
      cache: "no-store",
    }
  );
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Failed to fetch embedding status (HTTP ${res.status})`
    );
  }
  return res.json();
}

/**
 * Execute semantic vector search across document chunks.
 */
export async function vectorSearch(
  request: VectorSearchRequest
): Promise<VectorSearchResponse> {
  const res = await fetch(`${API_BASE_URL}/api/search/vector`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Vector search failed (HTTP ${res.status})`
    );
  }
  return res.json();
}

/**
 * Trigger global or batch reindexing of embeddings.
 */
export async function reindexEmbeddings(
  force = false,
  documentIds?: string[]
): Promise<ReindexResponse> {
  const res = await fetch(`${API_BASE_URL}/api/embeddings/reindex`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ force, document_ids: documentIds }),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(
      errorData.detail || `Reindexing failed (HTTP ${res.status})`
    );
  }
  return res.json();
}



// ── Step 7: Entity Extraction Types & API Functions ──────────────────────────

export interface EntityResponse {
  id: string;
  entity_type: string;
  canonical_name: string;
  display_name: string;
  description?: string | null;
  mention_count: number;
  document_count: number;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface EntityListResponse {
  total: number;
  page: number;
  page_size: number;
  entities: EntityResponse[];
}

export interface ChunkEntityMention {
  id: string;
  chunk_id: string;
  entity_id: string;
  document_id: string;
  mention_text: string;
  confidence: number;
  entity_type: string;
  canonical_name: string;
  section_header?: string | null;
  page_number?: number | null;
}

export interface DocumentEntityMentionsResponse {
  total: number;
  page: number;
  page_size: number;
  document_id: string;
  entities: ChunkEntityMention[];
}

export interface DocumentEntityStatusResponse {
  document_id: string;
  entity_extraction_status: string;
  entity_mention_count: number;
  unique_entity_count: number;
  total_chunks: number;
}

export interface EntityExtractionTaskResponse {
  document_id: string;
  task: string;
  status: string;
  message: string;
}

/** Trigger entity extraction for a document */
export async function extractDocumentEntities(
  documentId: string,
  force: boolean = false
): Promise<EntityExtractionTaskResponse> {
  const params = force ? "?force=true" : "";
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/entities/extract${params}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Entity extraction failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** Get entity extraction status for a document */
export async function getDocumentEntityStatus(
  documentId: string
): Promise<DocumentEntityStatusResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/entities/status`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** List entity mentions for a document with optional filters */
export async function listDocumentEntities(
  documentId: string,
  params?: {
    entity_type?: string;
    search?: string;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }
): Promise<DocumentEntityMentionsResponse> {
  const qs = new URLSearchParams();
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.search) qs.set("search", params.search);
  if (params?.min_confidence != null) qs.set("min_confidence", String(params.min_confidence));
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/entities${query}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Search canonical entities */
export async function searchEntities(
  q: string,
  params?: { entity_type?: string; page?: number; page_size?: number }
): Promise<EntityListResponse> {
  const qs = new URLSearchParams({ q });
  if (params?.entity_type) qs.set("entity_type", params.entity_type);
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const res = await fetch(`${API_BASE_URL}/api/entities/search?${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get a canonical entity by ID */
export async function getEntity(entityId: string): Promise<EntityResponse> {
  const res = await fetch(`${API_BASE_URL}/api/entities/${entityId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


// ── Step 8: Relationship Extraction Types & API Functions ─────────────────────

export interface EntitySummary {
  id: string;
  canonical_name: string;
  display_name: string;
  entity_type: string;
}

export interface RelationshipResponse {
  id: string;
  source_entity: EntitySummary;
  target_entity: EntitySummary;
  relationship_type: string;
  confidence: number;
  evidence_text?: string | null;
  chunk_id: string;
  document_id: string;
  source_start_char?: number | null;
  source_end_char?: number | null;
  target_start_char?: number | null;
  target_end_char?: number | null;
  provider?: string | null;
  model?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface RelationshipListResponse {
  total: number;
  page: number;
  page_size: number;
  relationships: RelationshipResponse[];
}

export interface EntityRelationshipsResponse {
  entity_id: string;
  total_outgoing: number;
  total_incoming: number;
  outgoing: RelationshipResponse[];
  incoming: RelationshipResponse[];
}

export interface DocumentRelationshipStatusResponse {
  document_id: string;
  relationship_extraction_status: string;
  total_chunks: number;
  processed_chunks: number;
  relationships: number;
  failed_chunks: number;
}

export interface RelationshipExtractionTaskResponse {
  document_id: string;
  task: string;
  status: string;
  message: string;
  stats?: {
    document_id: string;
    total_chunks: number;
    processed_chunks: number;
    relationships_found: number;
    relationships_created: number;
    unresolved: number;
    skipped: number;
    failed_chunks: number;
  } | null;
}

/** Trigger relationship extraction for a document */
export async function extractDocumentRelationships(
  documentId: string,
  force: boolean = false
): Promise<RelationshipExtractionTaskResponse> {
  const params = force ? "?force=true" : "";
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/relationships/extract${params}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Relationship extraction failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** Get relationship extraction status for a document */
export async function getDocumentRelationshipStatus(
  documentId: string
): Promise<DocumentRelationshipStatusResponse> {
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/relationships/status`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** List extracted relationships for a document */
export async function listDocumentRelationships(
  documentId: string,
  params?: {
    relationship_type?: string;
    source_entity_id?: string;
    target_entity_id?: string;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }
): Promise<RelationshipListResponse> {
  const qs = new URLSearchParams();
  if (params?.relationship_type) qs.set("relationship_type", params.relationship_type);
  if (params?.source_entity_id) qs.set("source_entity_id", params.source_entity_id);
  if (params?.target_entity_id) qs.set("target_entity_id", params.target_entity_id);
  if (params?.min_confidence != null) qs.set("min_confidence", String(params.min_confidence));
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const query = qs.toString() ? `?${qs}` : "";
  const res = await fetch(
    `${API_BASE_URL}/api/documents/${documentId}/relationships${query}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get incoming and outgoing relationships for a specific entity */
export async function getEntityRelationships(
  entityId: string,
  page: number = 1,
  pageSize: number = 50
): Promise<EntityRelationshipsResponse> {
  const qs = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
  });
  const res = await fetch(
    `${API_BASE_URL}/api/entities/${entityId}/relationships?${qs}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get single relationship detail by ID */
export async function getRelationship(
  relationshipId: string
): Promise<RelationshipResponse> {
  const res = await fetch(`${API_BASE_URL}/api/relationships/${relationshipId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Search relationships across entities, type, and evidence */
export async function searchRelationships(
  q: string,
  params?: {
    relationship_type?: string;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }
): Promise<RelationshipListResponse> {
  const qs = new URLSearchParams({ q });
  if (params?.relationship_type) qs.set("relationship_type", params.relationship_type);
  if (params?.min_confidence != null) qs.set("min_confidence", String(params.min_confidence));
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const res = await fetch(`${API_BASE_URL}/api/relationships/search?${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}


// ── Step 9: Neo4j Knowledge Graph Types & API Functions ──────────────────────

export interface GraphNode {
  id: string;
  label: string;
  entity_type: string;
  canonical_name: string;
  display_name: string;
  description?: string | null;
  properties?: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: string;
  confidence: number;
  evidence_text?: string | null;
  document_id?: string | null;
  chunk_id?: string | null;
  source_start_char?: number | null;
  source_end_char?: number | null;
  target_start_char?: number | null;
  target_end_char?: number | null;
  properties?: Record<string, any>;
}

export interface SubgraphResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
  truncated: boolean;
  total_nodes: number;
  total_edges: number;
}

export interface DocumentProvenance {
  document_id: string;
  filename: string;
  mention_count: number;
}

export interface GraphEntityDetailResponse {
  entity: GraphNode;
  incoming: GraphEdge[];
  outgoing: GraphEdge[];
  documents: DocumentProvenance[];
  total_incoming: number;
  total_outgoing: number;
}

export interface GraphNeighborsResponse {
  entity_id: string;
  depth: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphSyncResponse {
  documents_synced: number;
  chunks_synced: number;
  entities_synced: number;
  mentions_synced: number;
  relationships_synced: number;
  errors: number;
  duration_ms: number;
  message: string;
}

export interface GraphHealthResponse {
  status: string;
  database: string;
  connected: boolean;
  node_count?: number | null;
  relationship_count?: number | null;
  error?: string | null;
}

/** Synchronize PostgreSQL documents, chunks, entities, and relationships to Neo4j */
export async function syncKnowledgeGraph(
  documentId?: string,
  force: boolean = false
): Promise<GraphSyncResponse> {
  const qs = new URLSearchParams();
  if (documentId) qs.set("document_id", documentId);
  if (force) qs.set("force", "true");
  const query = qs.toString() ? `?${qs}` : "";
  const res = await fetch(`${API_BASE_URL}/api/graph/sync${query}`, {
    method: "POST",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Graph synchronization failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** Search entities directly in Neo4j Knowledge Graph */
export async function searchGraphEntities(
  q: string,
  limit: number = 20
): Promise<GraphNode[]> {
  const qs = new URLSearchParams({ q, limit: String(limit) });
  const res = await fetch(`${API_BASE_URL}/api/graph/entities/search?${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get full graph entity details with connected edges and document references */
export async function getGraphEntity(
  entityId: string
): Promise<GraphEntityDetailResponse> {
  const res = await fetch(`${API_BASE_URL}/api/graph/entities/${entityId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get N-hop neighbors for an entity in the graph */
export async function getGraphNeighbors(
  entityId: string,
  depth: number = 1,
  relationshipType?: string,
  limit: number = 50
): Promise<GraphNeighborsResponse> {
  const qs = new URLSearchParams({
    depth: String(depth),
    limit: String(limit),
  });
  if (relationshipType) qs.set("relationship_type", relationshipType);
  const res = await fetch(
    `${API_BASE_URL}/api/graph/entities/${entityId}/neighbors?${qs}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get bounded subgraph centered on an entity for visualization */
export async function getEntitySubgraph(
  entityId: string,
  depth: number = 2,
  maxNodes: number = 100,
  maxRelationships: number = 200
): Promise<SubgraphResponse> {
  const qs = new URLSearchParams({
    depth: String(depth),
    max_nodes: String(maxNodes),
    max_relationships: String(maxRelationships),
  });
  const res = await fetch(
    `${API_BASE_URL}/api/graph/subgraph/${entityId}?${qs}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get document-scoped subgraph */
export async function getDocumentSubgraph(
  documentId: string,
  maxNodes: number = 100,
  maxRelationships: number = 200
): Promise<SubgraphResponse> {
  const qs = new URLSearchParams({
    max_nodes: String(maxNodes),
    max_relationships: String(maxRelationships),
  });
  const res = await fetch(
    `${API_BASE_URL}/api/graph/document/${documentId}?${qs}`
  );
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Check Neo4j health and topology metrics */
export async function getNeo4jHealth(): Promise<GraphHealthResponse> {
  const res = await fetch(`${API_BASE_URL}/api/health/neo4j`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ──────────────────────────────────────────────────────────────────────────
// Step 10+ — Copilot, Ingestion Orchestrator, Evaluation & Analytics API
// ──────────────────────────────────────────────────────────────────────────

export interface CopilotCitation {
  citation_index: number;
  document_id: string;
  document_name: string;
  chunk_id: string;
  page_start?: number | null;
  page_end?: number | null;
  section_title?: string | null;
  excerpt: string;
  relevance_score: number;
  evidence_type: string;
}

export interface CopilotMessage {
  id: string;
  conversation_id: string;
  sender: "user" | "copilot";
  content: string;
  grounding_score?: number | null;
  query_category?: string | null;
  citations: CopilotCitation[];
  retrieval_metadata?: any;
  created_at: string;
}

export interface CopilotChatInput {
  message: string;
  conversation_id?: string | null;
  department?: string | null;
  document_ids?: string[] | null;
  include_graph?: boolean;
  max_depth?: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: CopilotMessage[];
}

export interface IngestionJob {
  id: string;
  document_id: string;
  job_type: string;
  status: "pending" | "running" | "completed" | "failed";
  current_step: string;
  progress_pct: number;
  error_message?: string | null;
  details?: any;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
}

export interface EvaluationQueryItem {
  id: string;
  query: string;
  expected_answer?: string | null;
  actual_answer: string;
  groundedness_score: number;
  citation_coverage: number;
  latency_ms: number;
  metrics?: any;
  created_at: string;
}

export interface EvaluationRunDetail {
  id: string;
  name: string;
  status: string;
  total_queries: number;
  avg_recall: number;
  avg_precision: number;
  avg_groundedness: number;
  avg_citation_coverage: number;
  hallucination_rate: number;
  avg_latency_ms: number;
  created_at: string;
  results: EvaluationQueryItem[];
}

export interface DashboardAnalytics {
  documents_total: number;
  chunks_total: number;
  entities_total: number;
  relationships_total: number;
  conversations_total: number;
  messages_total: number;
  avg_grounding_score: number;
  department_distribution: { department: string; count: number }[];
  entity_type_distribution: { entity_type: string; count: number }[];
  feedback_breakdown: { rating: string; count: number }[];
  graph_status: { status: string; nodes: number; edges: number; [key: string]: any };
}

/** Send message to Copilot and receive grounded response with citations */
export async function sendCopilotChat(
  input: CopilotChatInput
): Promise<CopilotMessage> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Copilot chat request failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** Stream Copilot message tokens via Server-Sent Events (SSE) */
export async function streamCopilotChat(
  input: CopilotChatInput,
  onToken: (token: string) => void,
  onMetadata?: (meta: any) => void,
  onCitations?: (citations: any[], groundingScore: number) => void,
  onSubgraph?: (subgraph: any) => void
): Promise<{ id: string; conversation_id: string; content: string; traversed_subgraph?: any }> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Copilot streaming failed (HTTP ${res.status})`);
  }

  const reader = res.body?.getReader();
  if (!reader) throw new Error("Response body is not readable");

  const decoder = new TextDecoder();
  let accumulatedContent = "";
  let messageId = "";
  let convId = input.conversation_id || "";
  let buffer = "";
  let capturedSubgraph: any = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      try {
        const payload = JSON.parse(trimmed.slice(6));
        if (payload.event === "metadata") {
          if (payload.conversation_id) convId = payload.conversation_id;
          if (payload.traversed_subgraph) {
            capturedSubgraph = payload.traversed_subgraph;
            if (onSubgraph) onSubgraph(payload.traversed_subgraph);
          }
          if (onMetadata) onMetadata(payload);
        } else if (payload.event === "token") {
          accumulatedContent += payload.token;
          onToken(payload.token);
        } else if (payload.event === "citations" && onCitations) {
          onCitations(payload.citations, payload.grounding_score);
        } else if (payload.event === "done") {
          messageId = payload.message_id || messageId;
          convId = payload.conversation_id || convId;
          if (payload.traversed_subgraph) {
            capturedSubgraph = payload.traversed_subgraph;
            if (onSubgraph) onSubgraph(payload.traversed_subgraph);
          }
          if (payload.citations && onCitations) {
            onCitations(payload.citations, payload.grounding_score);
          }
        }
      } catch {
        // Skip malformed chunks
      }
    }
  }

  return { id: messageId, conversation_id: convId, content: accumulatedContent, traversed_subgraph: capturedSubgraph };
}

/** Fetch recent Copilot conversation sessions */
export async function listConversations(limit: number = 30): Promise<ConversationSummary[]> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/conversations?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Fetch conversation details and full message history */
export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/conversations/${conversationId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Delete a conversation session */
export async function deleteConversation(conversationId: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/conversations/${conversationId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
}

/** Submit feedback on a Copilot message */
export async function submitMessageFeedback(
  messageId: string,
  rating: "helpful" | "not_helpful" | "incorrect" | "missing_info",
  feedbackText?: string
): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/copilot/messages/${messageId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rating, feedback_text: feedbackText }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Trigger full ingestion pipeline: text -> chunk -> embed -> entities -> relationships -> Neo4j */
export async function triggerFullPipeline(
  documentId: string,
  forceRetry: boolean = false
): Promise<IngestionJob> {
  const res = await fetch(
    `${API_BASE_URL}/api/jobs/documents/${documentId}/pipeline?force_retry=${forceRetry}`,
    { method: "POST" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Pipeline execution failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** Get status of an ingestion job */
export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/${jobId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get latest ingestion job for document */
export async function getLatestDocumentJob(documentId: string): Promise<IngestionJob | null> {
  const res = await fetch(`${API_BASE_URL}/api/jobs/documents/${documentId}/latest`);
  if (!res.ok) return null;
  return res.json();
}

/** Trigger evaluation benchmark run */
export async function runEvaluationBenchmark(
  name: string = "Enterprise Evaluation Run"
): Promise<EvaluationRunDetail> {
  const res = await fetch(`${API_BASE_URL}/api/evaluation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Evaluation run failed (HTTP ${res.status})`);
  }
  return res.json();
}

/** List historical evaluation runs */
export async function listEvaluationRuns(limit: number = 20): Promise<any[]> {
  const res = await fetch(`${API_BASE_URL}/api/evaluation/runs?limit=${limit}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Get full evaluation run details */
export async function getEvaluationRun(runId: string): Promise<EvaluationRunDetail> {
  const res = await fetch(`${API_BASE_URL}/api/evaluation/runs/${runId}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/** Fetch live platform analytics and metrics */
export async function getDashboardAnalytics(): Promise<DashboardAnalytics> {
  const res = await fetch(`${API_BASE_URL}/api/analytics/dashboard`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
