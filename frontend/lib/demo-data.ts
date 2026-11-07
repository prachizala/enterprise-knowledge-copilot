/**
 * Centralized Demo Data for Enterprise Knowledge Copilot
 * Used for frontend presentation and UI states during Step 2.
 * Real backend integrations will replace these in future steps.
 */

export interface StatItem {
  id: string;
  label: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
  description: string;
}

export const DASHBOARD_STATS: StatItem[] = [
  {
    id: "docs",
    label: "Documents",
    value: "1,248",
    change: "+12 this week",
    trend: "up",
    description: "Ingested enterprise files across 6 departments",
  },
  {
    id: "entities",
    label: "Entities",
    value: "18,420",
    change: "+326 this week",
    trend: "up",
    description: "Extracted concepts, people, and systems",
  },
  {
    id: "relationships",
    label: "Relationships",
    value: "42,830",
    change: "+1,240 this week",
    trend: "up",
    description: "Neo4j semantic graph connections",
  },
  {
    id: "queries",
    label: "Queries",
    value: "3,821",
    change: "+18% this week",
    trend: "up",
    description: "Hybrid GraphRAG user questions answered",
  },
];

export const EXAMPLE_QUESTIONS = [
  "Which projects use AWS?",
  "What policies apply to Project Alpha?",
  "Who manages Project Beta?",
  "What changed in the security policy?",
];

export interface RecentDocumentItem {
  id: string;
  name: string;
  type: "PDF" | "DOCX" | "TXT" | "CSV" | "MD";
  department: string;
  updated: string;
  status: "Processed" | "Processing" | "Failed" | "Uploaded";
  owner: string;
  chunks: number;
  entities: number;
  size: string;
  version?: string;
  created_at?: string;
  processed_at?: string | null;
  extracted_characters?: number;
  extracted_words?: number;
  extraction_status?: string;
  processing_error?: string | null;
  embedding_status?: "not_started" | "pending" | "processing" | "completed" | "failed";
  embedded_chunks?: number;
  embedding_model?: string | null;
  entity_extraction_status?: "not_started" | "processing" | "completed" | "partial" | "failed";
  entity_mention_count?: number;
  unique_entity_count?: number;
  relationship_extraction_status?: "not_started" | "processing" | "completed" | "partial" | "failed";
  relationship_count?: number;
}

export const RECENT_DOCUMENTS: RecentDocumentItem[] = [
  {
    id: "doc-1",
    name: "Security Policy.pdf",
    type: "PDF",
    department: "Security",
    updated: "2 hours ago",
    status: "Processed",
    owner: "Sarah Jenkins",
    chunks: 48,
    entities: 142,
    size: "2.4 MB",
  },
  {
    id: "doc-2",
    name: "Project Alpha.docx",
    type: "DOCX",
    department: "Engineering",
    updated: "Yesterday",
    status: "Processed",
    owner: "Marcus Vance",
    chunks: 112,
    entities: 384,
    size: "4.1 MB",
  },
  {
    id: "doc-3",
    name: "Customer Architecture.pdf",
    type: "PDF",
    department: "Engineering",
    updated: "2 days ago",
    status: "Processed",
    owner: "Elena Rostova",
    chunks: 64,
    entities: 219,
    size: "3.7 MB",
  },
  {
    id: "doc-4",
    name: "HR Guidelines.pdf",
    type: "PDF",
    department: "Human Resources",
    updated: "3 days ago",
    status: "Processed",
    owner: "David Kim",
    chunks: 35,
    entities: 88,
    size: "1.2 MB",
  },
  {
    id: "doc-5",
    name: "Q3 Financial Summary.csv",
    type: "CSV",
    department: "Finance",
    updated: "4 days ago",
    status: "Processed",
    owner: "Amanda Cruz",
    chunks: 28,
    entities: 165,
    size: "820 KB",
  },
  {
    id: "doc-6",
    name: "Vendor Data Privacy Agreement.pdf",
    type: "PDF",
    department: "Legal",
    updated: "5 days ago",
    status: "Processed",
    owner: "Julian Ross",
    chunks: 52,
    entities: 194,
    size: "1.8 MB",
  },
  {
    id: "doc-7",
    name: "Project Beta Technical Spec.docx",
    type: "DOCX",
    department: "Engineering",
    updated: "6 days ago",
    status: "Processed",
    owner: "Rachel Thorne",
    chunks: 89,
    entities: 310,
    size: "5.2 MB",
  },
];

export interface RecentQueryItem {
  id: string;
  query: string;
  timeAgo: string;
  entitiesMatched: number;
  sourcesCount: number;
}

export const RECENT_QUERIES: RecentQueryItem[] = [
  {
    id: "q-1",
    query: "Which projects are affected by the new security policy?",
    timeAgo: "5 minutes ago",
    entitiesMatched: 4,
    sourcesCount: 3,
  },
  {
    id: "q-2",
    query: "Who manages Project Alpha?",
    timeAgo: "18 minutes ago",
    entitiesMatched: 2,
    sourcesCount: 2,
  },
  {
    id: "q-3",
    query: "Which products depend on AWS?",
    timeAgo: "1 hour ago",
    entitiesMatched: 6,
    sourcesCount: 4,
  },
  {
    id: "q-4",
    query: "What is the data retention schedule for EU customer records?",
    timeAgo: "3 hours ago",
    entitiesMatched: 3,
    sourcesCount: 2,
  },
];

export interface GraphNode {
  id: string;
  label: string;
  type: "Project" | "Person" | "Product" | "Policy" | "Infrastructure";
  description: string;
  department: string;
  x: number;
  y: number;
  relationships: {
    predicate: string;
    targetId: string;
    targetLabel: string;
    targetType: string;
  }[];
}

export const GRAPH_DEMO_NODES: GraphNode[] = [
  {
    id: "node-project-alpha",
    label: "Project Alpha",
    type: "Project",
    description: "Core high-throughput enterprise event stream integration engine.",
    department: "Engineering",
    x: 400,
    y: 220,
    relationships: [
      { predicate: "MANAGED_BY", targetId: "node-marcus", targetLabel: "Marcus Vance", targetType: "Person" },
      { predicate: "USES", targetId: "node-aws", targetLabel: "AWS GovCloud", targetType: "Infrastructure" },
      { predicate: "FOLLOWS", targetId: "node-policy-sec", targetLabel: "Security Policy 2026", targetType: "Policy" },
      { predicate: "POWERS", targetId: "node-product-core", targetLabel: "Enterprise Data Hub", targetType: "Product" },
    ],
  },
  {
    id: "node-marcus",
    label: "Marcus Vance",
    type: "Person",
    description: "Lead Principal Architect and Engineering Director.",
    department: "Engineering",
    x: 180,
    y: 110,
    relationships: [
      { predicate: "MANAGES", targetId: "node-project-alpha", targetLabel: "Project Alpha", targetType: "Project" },
      { predicate: "AUTHORED", targetId: "node-policy-sec", targetLabel: "Security Policy 2026", targetType: "Policy" },
    ],
  },
  {
    id: "node-elena",
    label: "Elena Rostova",
    type: "Person",
    description: "Staff Infrastructure and Cloud Systems Specialist.",
    department: "Engineering",
    x: 170,
    y: 330,
    relationships: [
      { predicate: "CONTRIBUTES_TO", targetId: "node-project-alpha", targetLabel: "Project Alpha", targetType: "Project" },
      { predicate: "MANAGES", targetId: "node-aws", targetLabel: "AWS GovCloud", targetType: "Infrastructure" },
    ],
  },
  {
    id: "node-product-core",
    label: "Enterprise Data Hub",
    type: "Product",
    description: "Unified analytics and data federation service.",
    department: "Product",
    x: 620,
    y: 110,
    relationships: [
      { predicate: "POWERED_BY", targetId: "node-project-alpha", targetLabel: "Project Alpha", targetType: "Project" },
      { predicate: "GOVERNED_BY", targetId: "node-policy-ret", targetLabel: "Data Retention Policy", targetType: "Policy" },
    ],
  },
  {
    id: "node-policy-sec",
    label: "Security Policy 2026",
    type: "Policy",
    description: "Mandatory zero-trust network encryption and compliance mandate.",
    department: "Security",
    x: 630,
    y: 320,
    relationships: [
      { predicate: "APPLIES_TO", targetId: "node-project-alpha", targetLabel: "Project Alpha", targetType: "Project" },
      { predicate: "APPLIES_TO", targetId: "node-aws", targetLabel: "AWS GovCloud", targetType: "Infrastructure" },
    ],
  },
  {
    id: "node-policy-ret",
    label: "Data Retention Policy",
    type: "Policy",
    description: "Statutory 7-year audit retention requirement for financial & PII records.",
    department: "Legal",
    x: 750,
    y: 200,
    relationships: [
      { predicate: "GOVERNS", targetId: "node-product-core", targetLabel: "Enterprise Data Hub", targetType: "Product" },
    ],
  },
  {
    id: "node-aws",
    label: "AWS GovCloud",
    type: "Infrastructure",
    description: "FIPS 140-3 compliant cloud hosting infrastructure.",
    department: "DevOps",
    x: 390,
    y: 410,
    relationships: [
      { predicate: "HOSTS", targetId: "node-project-alpha", targetLabel: "Project Alpha", targetType: "Project" },
    ],
  },
];

export interface TraversedSubgraphData {
  nodes: {
    id: string;
    label: string;
    canonical_name?: string;
    display_name?: string;
    entity_type: string;
    description?: string;
  }[];
  edges: {
    id: string;
    source: string;
    target: string;
    type: string;
    confidence?: number;
    evidence_text?: string;
  }[];
  paths?: string[];
  traversal_stats?: {
    nodes_count: number;
    edges_count: number;
    hops: number;
    query_category?: string;
  };
}

export interface CopilotMessage {
  id: string;
  sender: "user" | "copilot";
  timestamp: string;
  text: string;
  citations?: {
    id: number;
    title: string;
    location: string;
    snippet: string;
  }[];
  entitiesMatched?: string[];
  subgraphInsights?: string;
  traversedSubgraph?: TraversedSubgraphData;
}

export const INITIAL_COPILOT_MESSAGES: CopilotMessage[] = [
  {
    id: "msg-welcome",
    sender: "copilot",
    timestamp: "Just now",
    text: "Hello! I am your Enterprise Knowledge Copilot. I analyze relationships across documents, personnel, projects, and regulatory policies using Hybrid GraphRAG. Ask any question below to explore your knowledge base.",
  },
];

export const DEMO_COPILOT_RESPONSES: Record<string, CopilotMessage> = {
  default: {
    id: "demo-resp",
    sender: "copilot",
    timestamp: "Just now",
    text: "Based on our enterprise knowledge graph and verified documents, Project Alpha is actively deployed on AWS GovCloud with full compliance against the 2026 Security Policy. Marcus Vance leads engineering direction, while Elena Rostova oversees cloud infrastructure configurations.",
    citations: [
      {
        id: 1,
        title: "Security Policy.pdf",
        location: "Section 3.2, Page 14",
        snippet: "Zero-trust network architecture is mandatory for all projects interfacing with customer PII or AWS GovCloud workloads.",
      },
      {
        id: 2,
        title: "Project Alpha.docx",
        location: "Executive Summary, Page 2",
        snippet: "Project Alpha delivers high-throughput event federation, managed by Marcus Vance (Director of Engineering).",
      },
    ],
    entitiesMatched: ["Project Alpha", "AWS GovCloud", "Marcus Vance", "Security Policy 2026"],
    subgraphInsights: "Traversed 3 hops in Neo4j: [Project Alpha] --(MANAGED_BY)--> [Marcus Vance] --(AUTHORED)--> [Security Policy 2026]",
  },
};

export const ANALYTICS_DATA = {
  kpis: [
    { label: "Total Documents", value: "1,248", change: "+4.2%", period: "vs last month" },
    { label: "Entities Extracted", value: "18,420", change: "+12.1%", period: "vs last month" },
    { label: "Relationships Mapped", value: "42,830", change: "+15.8%", period: "vs last month" },
    { label: "Total Queries", value: "3,821", change: "+18.3%", period: "vs last month" },
    { label: "Avg. Response Time", value: "420 ms", change: "-8.5%", period: "latency reduction" },
    { label: "Citation Coverage", value: "98.4%", change: "+2.1%", period: "grounded accuracy" },
  ],
  weeklyQueries: [
    { day: "Mon", count: 420 },
    { day: "Tue", count: 580 },
    { day: "Wed", count: 710 },
    { day: "Thu", count: 640 },
    { day: "Fri", count: 820 },
    { day: "Sat", count: 290 },
    { day: "Sun", count: 361 },
  ],
  entityDistribution: [
    { type: "Projects", count: 240, percentage: 35, color: "bg-indigo-500" },
    { type: "People & Roles", count: 520, percentage: 25, color: "bg-blue-500" },
    { type: "Policies & Standards", count: 180, percentage: 20, color: "bg-purple-500" },
    { type: "Products & Systems", count: 310, percentage: 12, color: "bg-emerald-500" },
    { type: "Infrastructure", count: 140, percentage: 8, color: "bg-amber-500" },
  ],
  latencyBreakdown: [
    { stage: "Vector Embedding Search", durationMs: 110, percentage: 26 },
    { stage: "Neo4j Graph Traversal", durationMs: 140, percentage: 33 },
    { stage: "Hybrid RRF Reranking", durationMs: 40, percentage: 10 },
    { stage: "LLM Citation Generation", durationMs: 130, percentage: 31 },
  ],
  topEntitiesQueried: [
    { name: "Project Alpha", type: "Project", queryCount: 382, department: "Engineering" },
    { name: "Security Policy 2026", type: "Policy", queryCount: 294, department: "Security" },
    { name: "AWS GovCloud", type: "Infrastructure", queryCount: 215, department: "DevOps" },
    { name: "Elena Rostova", type: "Person", queryCount: 178, department: "Engineering" },
    { name: "Data Retention Mandate", type: "Policy", queryCount: 142, department: "Legal" },
  ],
};
