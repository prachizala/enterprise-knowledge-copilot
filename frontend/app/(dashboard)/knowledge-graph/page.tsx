"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import { EntityInspector } from "@/components/graph/EntityInspector";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import {
  GraphNode as ApiGraphNode,
  GraphEdge as ApiGraphEdge,
  GraphEntityDetailResponse,
  GraphHealthResponse,
  GraphSyncResponse,
  getNeo4jHealth,
  searchGraphEntities,
  getGraphEntity,
  getGraphNeighbors,
  getEntitySubgraph,
  syncKnowledgeGraph,
} from "@/lib/api";
import {
  Network,
  Sparkles,
  Filter,
  RefreshCw,
  Database,
  CheckCircle2,
  AlertCircle,
  ShieldCheck,
  Layers,
  ChevronDown,
  Info,
} from "lucide-react";

const ENTITY_TYPES = [
  "All",
  "ORGANIZATION",
  "PERSON",
  "PROJECT",
  "PRODUCT",
  "TECHNOLOGY",
  "LOCATION",
  "POLICY",
  "CONTRACT",
  "DEPARTMENT",
];

// Fallback demo graph in case Neo4j has 0 entities synced yet
const DEMO_FALLBACK_NODES: ApiGraphNode[] = [
  {
    id: "demo-alpha",
    label: "Project Alpha",
    canonical_name: "Project Alpha",
    display_name: "Project Alpha",
    entity_type: "PROJECT",
    description: "Core high-throughput enterprise event stream integration engine.",
  },
  {
    id: "demo-marcus",
    label: "Marcus Vance",
    canonical_name: "Marcus Vance",
    display_name: "Marcus Vance",
    entity_type: "PERSON",
    description: "Lead Principal Architect and Engineering Director.",
  },
  {
    id: "demo-aws",
    label: "AWS GovCloud",
    canonical_name: "AWS GovCloud",
    display_name: "AWS GovCloud",
    entity_type: "TECHNOLOGY",
    description: "FIPS 140-3 compliant cloud hosting infrastructure.",
  },
  {
    id: "demo-sec-policy",
    label: "Security Policy 2026",
    canonical_name: "Security Policy 2026",
    display_name: "Security Policy 2026",
    entity_type: "POLICY",
    description: "Mandatory zero-trust network encryption and compliance mandate.",
  },
  {
    id: "demo-datahub",
    label: "Enterprise Data Hub",
    canonical_name: "Enterprise Data Hub",
    display_name: "Enterprise Data Hub",
    entity_type: "PRODUCT",
    description: "Unified analytics and data federation service.",
  },
];

const DEMO_FALLBACK_EDGES: ApiGraphEdge[] = [
  {
    id: "demo-edge-1",
    source: "demo-alpha",
    target: "demo-marcus",
    type: "MANAGED_BY",
    confidence: 0.96,
    evidence_text: "Project Alpha is led and managed by Engineering Director Marcus Vance.",
    document_id: "demo-doc-1",
    chunk_id: "demo-chunk-1",
  },
  {
    id: "demo-edge-2",
    source: "demo-alpha",
    target: "demo-aws",
    type: "USES",
    confidence: 0.94,
    evidence_text: "The integration engine utilizes AWS GovCloud for secure enterprise workloads.",
    document_id: "demo-doc-1",
    chunk_id: "demo-chunk-2",
  },
  {
    id: "demo-edge-3",
    source: "demo-alpha",
    target: "demo-sec-policy",
    type: "GOVERNED_BY",
    confidence: 0.91,
    evidence_text: "Architecture must strictly conform to Security Policy 2026 requirements.",
    document_id: "demo-doc-2",
    chunk_id: "demo-chunk-5",
  },
  {
    id: "demo-edge-4",
    source: "demo-datahub",
    target: "demo-alpha",
    type: "INTEGRATES_WITH",
    confidence: 0.89,
    evidence_text: "Enterprise Data Hub ingests high-volume real-time feeds via Project Alpha.",
    document_id: "demo-doc-3",
    chunk_id: "demo-chunk-9",
  },
];

export default function KnowledgeGraphPage() {
  const [nodes, setNodes] = useState<ApiGraphNode[]>([]);
  const [edges, setEdges] = useState<ApiGraphEdge[]>([]);
  const [selectedNode, setSelectedNode] = useState<ApiGraphNode | null>(null);
  const [selectedEdge, setSelectedEdge] = useState<ApiGraphEdge | null>(null);
  const [entityDetail, setEntityDetail] = useState<GraphEntityDetailResponse | null>(null);

  const [search, setSearch] = useState("");
  const [searchResults, setSearchResults] = useState<ApiGraphNode[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);

  const [selectedType, setSelectedType] = useState("All");
  const [neo4jHealth, setNeo4jHealth] = useState<GraphHealthResponse | null>(null);

  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [isExpandingNeighbors, setIsExpandingNeighbors] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [isTruncated, setIsTruncated] = useState(false);

  // Load initial health & graph on mount
  useEffect(() => {
    checkHealthAndInit();
  }, []);

  const checkHealthAndInit = async () => {
    setIsLoading(true);
    try {
      const health = await getNeo4jHealth().catch(() => null);
      setNeo4jHealth(health);

      if (health && health.connected && (health.node_count ?? 0) > 0) {
        // Query top entities
        const topEntities = await searchGraphEntities("", 30).catch(() => []);
        if (topEntities.length > 0) {
          const root = topEntities[0];
          const subgraph = await getEntitySubgraph(root.id, 2, 50, 100).catch(() => null);
          if (subgraph && subgraph.nodes.length > 0) {
            setNodes(subgraph.nodes);
            setEdges(subgraph.edges);
            setIsTruncated(subgraph.truncated);
            setSelectedNode(root);
            loadEntityDetails(root.id);
            setIsLoading(false);
            return;
          }
        }
      }

      // If Neo4j is offline or empty, use fallback demo topology
      setNodes(DEMO_FALLBACK_NODES);
      setEdges(DEMO_FALLBACK_EDGES);
      setSelectedNode(DEMO_FALLBACK_NODES[0]);
    } catch (e) {
      console.error("Knowledge Graph initialization error:", e);
      setNodes(DEMO_FALLBACK_NODES);
      setEdges(DEMO_FALLBACK_EDGES);
      setSelectedNode(DEMO_FALLBACK_NODES[0]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadEntityDetails = async (entityId: string) => {
    setIsLoadingDetail(true);
    try {
      const detail = await getGraphEntity(entityId).catch(() => null);
      setEntityDetail(detail);
    } catch (e) {
      console.error("Error loading entity details:", e);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  const handleSelectNode = (node: ApiGraphNode) => {
    setSelectedNode(node);
    setSelectedEdge(null);
    loadEntityDetails(node.id);
  };

  const handleSelectNodeById = (nodeId: string) => {
    const existing = nodes.find((n) => n.id === nodeId);
    if (existing) {
      handleSelectNode(existing);
    } else {
      // Load details and subgraph for unindexed neighbor
      loadSubgraphForNodeId(nodeId);
    }
  };

  const handleSelectEdge = (edge: ApiGraphEdge) => {
    setSelectedEdge(edge);
  };

  const loadSubgraphForNodeId = async (nodeId: string) => {
    setIsLoading(true);
    try {
      const subgraph = await getEntitySubgraph(nodeId, 2, 50, 100);
      if (subgraph && subgraph.nodes.length > 0) {
        setNodes(subgraph.nodes);
        setEdges(subgraph.edges);
        setIsTruncated(subgraph.truncated);
        const current = subgraph.nodes.find((n) => n.id === nodeId) || subgraph.nodes[0];
        setSelectedNode(current);
        loadEntityDetails(current.id);
      }
    } catch (e) {
      console.error("Error loading entity subgraph:", e);
    } finally {
      setIsLoading(false);
    }
  };

  const handleExpandNeighbors = async () => {
    if (!selectedNode) return;
    setIsExpandingNeighbors(true);
    try {
      const neighbors = await getGraphNeighbors(selectedNode.id, 1);
      if (neighbors && neighbors.nodes.length > 0) {
        // Merge nodes and edges
        setNodes((prev) => {
          const map = new Map(prev.map((n) => [n.id, n]));
          neighbors.nodes.forEach((n) => map.set(n.id, n));
          return Array.from(map.values());
        });
        setEdges((prev) => {
          const map = new Map(prev.map((e) => [e.id, e]));
          neighbors.edges.forEach((e) => map.set(e.id, e));
          return Array.from(map.values());
        });
      }
    } catch (e) {
      console.error("Error expanding neighbors:", e);
    } finally {
      setIsExpandingNeighbors(false);
    }
  };

  const handleSyncKnowledgeGraph = async () => {
    setIsSyncing(true);
    setSyncStatus("Synchronizing documents and entities to Neo4j...");
    try {
      const result = await syncKnowledgeGraph(undefined, true);
      setSyncStatus(
        `Sync Complete: ${result.entities_synced} entities, ${result.relationships_synced} relationships synchronized across ${result.documents_synced} documents.`
      );
      // Refresh health and graph
      await checkHealthAndInit();
    } catch (err: any) {
      setSyncStatus(`Sync Error: ${err.message || "Could not connect to Neo4j service."}`);
    } finally {
      setIsSyncing(false);
      setTimeout(() => {
        setSyncStatus(null);
      }, 7000);
    }
  };

  // Live entity search with debounce
  useEffect(() => {
    if (!search.trim()) {
      setSearchResults([]);
      setShowSearchDropdown(false);
      return;
    }
    const timer = setTimeout(async () => {
      setIsSearching(true);
      try {
        const results = await searchGraphEntities(search.trim(), 8);
        setSearchResults(results);
        setShowSearchDropdown(true);
      } catch (err) {
        // Fallback filter locally
        const filtered = nodes.filter(
          (n) =>
            (n.display_name || n.canonical_name || n.label)
              .toLowerCase()
              .includes(search.toLowerCase())
        );
        setSearchResults(filtered);
        setShowSearchDropdown(true);
      } finally {
        setIsSearching(false);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [search, nodes]);

  const filteredNodes = useMemo(() => {
    if (selectedType === "All") return nodes;
    return nodes.filter(
      (n) => (n.entity_type || "").toUpperCase() === selectedType.toUpperCase()
    );
  }, [nodes, selectedType]);

  const isConnected = neo4jHealth?.connected ?? false;

  return (
    <div className="space-y-6 pb-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              Knowledge Graph
            </h2>
            {/* Neo4j Status Badge */}
            <span
              className={`px-2.5 py-1 text-xs font-semibold rounded-full border flex items-center gap-1.5 ${
                isConnected
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-amber-500/10 text-amber-400 border-amber-500/30"
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  isConnected ? "bg-emerald-400 animate-pulse" : "bg-amber-400"
                }`}
              />
              {isConnected
                ? `Neo4j Online (${neo4jHealth?.node_count ?? nodes.length} nodes)`
                : "Standby / Preview"}
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Traverse enterprise entity relationships, ontologies, and multi-hop citations in Neo4j.
          </p>
        </div>

        {/* Header Right Actions: Search + Sync Button */}
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {/* Search Input with Auto-complete Dropdown */}
          <div className="relative w-full sm:w-64">
            <SearchInput
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClear={() => {
                setSearch("");
                setShowSearchDropdown(false);
              }}
              placeholder="Search graph entities..."
            />

            {showSearchDropdown && searchResults.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-1.5 p-1 rounded-xl bg-slate-900 border border-slate-800 shadow-2xl z-40 max-h-56 overflow-y-auto">
                {searchResults.map((entity) => (
                  <button
                    key={entity.id}
                    onClick={() => {
                      loadSubgraphForNodeId(entity.id);
                      setSearch("");
                      setShowSearchDropdown(false);
                    }}
                    className="w-full p-2 text-left rounded-lg hover:bg-slate-800 flex items-center justify-between text-xs transition-colors group"
                  >
                    <div>
                      <span className="font-semibold text-white group-hover:text-indigo-400">
                        {entity.display_name || entity.canonical_name || entity.label}
                      </span>
                      <span className="block text-[10px] text-slate-400 font-mono">
                        {entity.id}
                      </span>
                    </div>
                    <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-indigo-950/80 text-indigo-300 border border-indigo-500/30">
                      {entity.entity_type}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Sync Button */}
          <Button
            onClick={handleSyncKnowledgeGraph}
            disabled={isSyncing}
            variant="primary"
            size="sm"
            className="flex-shrink-0 text-xs font-semibold shadow-indigo-600/20"
          >
            <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${isSyncing ? "animate-spin" : ""}`} />
            <span>{isSyncing ? "Syncing..." : "Sync Graph"}</span>
          </Button>
        </div>
      </div>

      {/* Sync Status Toast/Banner */}
      {syncStatus && (
        <div className="p-3 rounded-xl bg-indigo-950/50 border border-indigo-800/60 text-xs text-indigo-200 flex items-center justify-between animate-fadeIn">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
            <span>{syncStatus}</span>
          </div>
          <button
            onClick={() => setSyncStatus(null)}
            className="text-slate-400 hover:text-white text-xs font-mono"
          >
            ✕
          </button>
        </div>
      )}

      {/* Filter Pills */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-slate-500 font-medium mr-1 flex items-center gap-1">
          <Filter className="w-3.5 h-3.5" /> Entity Filter:
        </span>
        {ENTITY_TYPES.map((type) => {
          const isActive = selectedType === type;
          return (
            <button
              key={type}
              onClick={() => setSelectedType(type)}
              className={`px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                isActive
                  ? "bg-indigo-600 text-white shadow-sm shadow-indigo-600/30 border border-indigo-500"
                  : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800 hover:bg-slate-800"
              }`}
            >
              {type}
            </button>
          );
        })}
      </div>

      {/* Truncation Warning */}
      {isTruncated && (
        <div className="p-2.5 rounded-xl bg-amber-950/30 border border-amber-800/40 text-xs text-amber-300 flex items-center gap-2">
          <Info className="w-4 h-4 text-amber-400 flex-shrink-0" />
          <span>
            Large graph detected. Subgraph bounded at 100 nodes for optimal visualization performance.
          </span>
        </div>
      )}

      {/* Main Graph Grid: Canvas (70%) + Inspector (30%) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <GraphCanvas
            nodes={filteredNodes}
            edges={edges}
            selectedNode={selectedNode}
            selectedEdge={selectedEdge}
            onSelectNode={handleSelectNode}
            onSelectEdge={handleSelectEdge}
            filteredType={selectedType}
            isLoading={isLoading}
          />
        </div>

        <div className="lg:col-span-1">
          <EntityInspector
            entity={selectedNode}
            entityDetail={entityDetail}
            selectedEdge={selectedEdge}
            isLoadingDetail={isLoadingDetail}
            isExpandingNeighbors={isExpandingNeighbors}
            onExpandNeighbors={handleExpandNeighbors}
            onSelectNodeById={handleSelectNodeById}
            onClearSelectedEdge={() => setSelectedEdge(null)}
          />
        </div>
      </div>
    </div>
  );
}
