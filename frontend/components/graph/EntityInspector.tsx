"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  GraphNode as ApiGraphNode,
  GraphEdge as ApiGraphEdge,
  GraphEntityDetailResponse,
} from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import {
  Network,
  Bot,
  Share2,
  FileText,
  ExternalLink,
  ChevronRight,
  Sparkles,
  ShieldCheck,
  Quote,
  Maximize,
  ArrowRight,
  Info,
} from "lucide-react";
import { getEntityColor } from "./GraphCanvas";

export interface EntityInspectorProps {
  entity: ApiGraphNode | null;
  entityDetail: GraphEntityDetailResponse | null;
  selectedEdge: ApiGraphEdge | null;
  isLoadingDetail?: boolean;
  isExpandingNeighbors?: boolean;
  onExpandNeighbors?: () => void;
  onSelectNodeById?: (id: string) => void;
  onClearSelectedEdge?: () => void;
}

export function EntityInspector({
  entity,
  entityDetail,
  selectedEdge,
  isLoadingDetail = false,
  isExpandingNeighbors = false,
  onExpandNeighbors,
  onSelectNodeById,
  onClearSelectedEdge,
}: EntityInspectorProps) {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"entity" | "evidence">("entity");

  // If an edge is explicitly selected, switch to evidence tab or view
  React.useEffect(() => {
    if (selectedEdge) {
      setActiveTab("evidence");
    } else {
      setActiveTab("entity");
    }
  }, [selectedEdge]);

  const handleAskCopilot = () => {
    const query = entity
      ? `What is the relationship between ${entity.display_name || entity.canonical_name} and other enterprise entities?`
      : selectedEdge
      ? `Explain the relationship ${selectedEdge.type} between source entity and target entity.`
      : "Explain the current knowledge graph topology.";
    router.push(`/copilot?q=${encodeURIComponent(query)}`);
  };

  // 1. Evidence Inspection View (when user clicks an edge or selects Evidence tab)
  if (selectedEdge && activeTab === "evidence") {
    const confidencePct = Math.round((selectedEdge.confidence ?? 0.8) * 100);

    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-sm p-5 space-y-4 shadow-xl flex flex-col justify-between h-[560px] overflow-y-auto">
        <div className="space-y-4">
          {/* Header */}
          <div className="pb-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                <Quote className="w-3.5 h-3.5" />
              </span>
              <div>
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Relationship Evidence
                </span>
                <h3 className="text-sm font-bold text-white font-mono">{selectedEdge.type}</h3>
              </div>
            </div>
            {entity && (
              <button
                onClick={() => {
                  onClearSelectedEdge?.();
                  setActiveTab("entity");
                }}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium"
              >
                Back to Node
              </button>
            )}
          </div>

          {/* Relationship Metrics */}
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                Confidence Score:
              </span>
              <span className="font-semibold text-emerald-400 font-mono">{confidencePct}%</span>
            </div>
            {/* Progress bar */}
            <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all"
                style={{ width: `${confidencePct}%` }}
              />
            </div>
          </div>

          {/* Evidence Snippet */}
          <div className="space-y-1.5">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Quote className="w-3 h-3 text-indigo-400" /> Grounded Text Evidence
            </span>
            <div className="p-3 rounded-xl bg-slate-950/90 border border-indigo-950/50 text-xs text-slate-300 leading-relaxed italic border-l-2 border-l-indigo-500">
              "{selectedEdge.evidence_text || "Direct structured relationship extracted from document provenance."}"
            </div>
          </div>

          {/* Provenance References */}
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800 space-y-1.5 text-xs">
            <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
              Provenance Provenance
            </span>
            <div className="flex justify-between text-slate-400">
              <span>Document ID:</span>
              <span className="font-mono text-[10px] text-slate-300 truncate max-w-[140px]">
                {selectedEdge.document_id || "N/A"}
              </span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Chunk ID:</span>
              <span className="font-mono text-[10px] text-slate-300 truncate max-w-[140px]">
                {selectedEdge.chunk_id || "N/A"}
              </span>
            </div>
          </div>
        </div>

        {/* CTA Button */}
        <div className="pt-3 border-t border-slate-800">
          <Button onClick={handleAskCopilot} variant="primary" size="sm" className="w-full text-xs">
            <Bot className="w-3.5 h-3.5 mr-1.5" />
            <span>Ask Copilot about this relationship</span>
          </Button>
        </div>
      </div>
    );
  }

  // 2. Empty State View
  if (!entity) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 text-center flex flex-col items-center justify-center h-[560px]">
        <Network className="w-10 h-10 text-slate-600 mb-3 animate-pulse" />
        <h4 className="text-sm font-semibold text-slate-300">No Entity Selected</h4>
        <p className="text-xs text-slate-500 mt-1.5 max-w-[220px] leading-relaxed">
          Select any node or edge on the Knowledge Graph canvas to inspect entities, relationships,
          and grounded evidence.
        </p>
      </div>
    );
  }

  // 3. Entity Detail View
  const color = getEntityColor(entity.entity_type);
  const displayName = entity.display_name || entity.canonical_name || entity.label;
  const canonicalName = entity.canonical_name || entity.label;
  const docs = entityDetail?.documents || [];
  const incoming = entityDetail?.incoming || [];
  const outgoing = entityDetail?.outgoing || [];
  const totalRels = incoming.length + outgoing.length;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-900/70 backdrop-blur-sm p-5 space-y-4 shadow-xl flex flex-col justify-between h-[560px] overflow-hidden">
      <div className="space-y-3.5 overflow-y-auto pr-1">
        {/* Header */}
        <div className="pb-3 border-b border-slate-800">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              Selected Entity
            </span>
            <span
              className="px-2 py-0.5 text-[10px] font-bold rounded-md border uppercase tracking-wider"
              style={{
                backgroundColor: color.bg,
                borderColor: color.stroke,
                color: color.text,
              }}
            >
              {entity.entity_type}
            </span>
          </div>
          <h3 className="text-base font-bold text-white mt-1.5 leading-snug">{displayName}</h3>
          {canonicalName !== displayName && (
            <p className="text-xs text-slate-400 font-mono mt-0.5">Canonical: {canonicalName}</p>
          )}
          {entity.description && (
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{entity.description}</p>
          )}
        </div>

        {/* Action: Expand Neighbors */}
        <div className="flex items-center gap-2">
          <Button
            onClick={onExpandNeighbors}
            disabled={isExpandingNeighbors}
            variant="secondary"
            size="sm"
            className="w-full text-xs font-medium border-slate-700 bg-slate-800/80 hover:bg-slate-700"
          >
            {isExpandingNeighbors ? (
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
                Expanding 1-Hop Graph...
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Maximize className="w-3.5 h-3.5 text-indigo-400" />
                Expand Neighbors
              </span>
            )}
          </Button>
        </div>

        {/* Document Provenance */}
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <FileText className="w-3 h-3 text-indigo-400" /> Document Provenance ({docs.length})
            </span>
          </div>
          {docs.length === 0 ? (
            <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-500">
              No direct document mentions indexed yet.
            </div>
          ) : (
            <div className="space-y-1 max-h-28 overflow-y-auto pr-0.5">
              {docs.map((doc, idx) => (
                <div
                  key={idx}
                  className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/70 flex items-center justify-between text-[11px]"
                >
                  <span className="text-slate-300 font-medium truncate max-w-[170px]" title={doc.filename}>
                    {doc.filename || "Enterprise Document"}
                  </span>
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono bg-indigo-950/70 text-indigo-300 border border-indigo-800/40">
                    {doc.mention_count} mention{doc.mention_count === 1 ? "" : "s"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Connected Graph Relationships */}
        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <Share2 className="w-3 h-3 text-indigo-400" /> Direct Relationships ({totalRels})
            </span>
            {isLoadingDetail && (
              <span className="text-[10px] text-indigo-400 animate-pulse font-mono">Syncing...</span>
            )}
          </div>

          <div className="space-y-1 max-h-36 overflow-y-auto pr-0.5">
            {outgoing.map((rel, idx) => (
              <div
                key={`out-${idx}`}
                className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/70 flex items-center justify-between text-[11px] hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-1.5 overflow-hidden">
                  <span className="px-1.5 py-0.5 rounded bg-indigo-950/80 text-indigo-300 font-mono text-[9px] border border-indigo-500/30 whitespace-nowrap">
                    {rel.type}
                  </span>
                  <ArrowRight className="w-2.5 h-2.5 text-slate-500 flex-shrink-0" />
                  <span
                    onClick={() => onSelectNodeById?.(rel.target)}
                    className="text-slate-200 font-medium hover:text-indigo-400 cursor-pointer truncate max-w-[110px]"
                    title={rel.target}
                  >
                    {rel.target}
                  </span>
                </div>
                <span className="text-[9px] text-emerald-400 font-mono">
                  {Math.round((rel.confidence || 0.8) * 100)}%
                </span>
              </div>
            ))}

            {incoming.map((rel, idx) => (
              <div
                key={`in-${idx}`}
                className="p-2 rounded-lg bg-slate-950/60 border border-slate-800/70 flex items-center justify-between text-[11px] hover:border-slate-700 transition-colors"
              >
                <div className="flex items-center gap-1.5 overflow-hidden">
                  <span
                    onClick={() => onSelectNodeById?.(rel.source)}
                    className="text-slate-200 font-medium hover:text-indigo-400 cursor-pointer truncate max-w-[110px]"
                    title={rel.source}
                  >
                    {rel.source}
                  </span>
                  <ArrowRight className="w-2.5 h-2.5 text-slate-500 flex-shrink-0" />
                  <span className="px-1.5 py-0.5 rounded bg-purple-950/80 text-purple-300 font-mono text-[9px] border border-purple-500/30 whitespace-nowrap">
                    {rel.type}
                  </span>
                </div>
                <span className="text-[9px] text-emerald-400 font-mono">
                  {Math.round((rel.confidence || 0.8) * 100)}%
                </span>
              </div>
            ))}

            {totalRels === 0 && !isLoadingDetail && (
              <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80 text-[11px] text-slate-500">
                No direct relationships found for this entity.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* CTA Button */}
      <div className="pt-3 border-t border-slate-800">
        <Button onClick={handleAskCopilot} variant="primary" size="sm" className="w-full text-xs">
          <Bot className="w-3.5 h-3.5 mr-1.5" />
          <span>Ask Copilot about this entity</span>
        </Button>
      </div>
    </div>
  );
}
