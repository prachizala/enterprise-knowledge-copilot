"use client";

import React, { useEffect } from "react";
import { TraversedSubgraphData } from "@/lib/demo-data";
import { TraversedGraphVisualizer } from "./TraversedGraphVisualizer";
import { Network, X, Sparkles, Layers, ShieldCheck, Box, Compass } from "lucide-react";
import { Badge } from "@/components/ui/Badge";

export interface TraversedGraphModalProps {
  isOpen: boolean;
  onClose: () => void;
  subgraph: TraversedSubgraphData | null;
  queryCategory?: string;
  queryText?: string;
}

export function TraversedGraphModal({
  isOpen,
  onClose,
  subgraph,
  queryCategory = "multi-hop traversal",
  queryText,
}: TraversedGraphModalProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !subgraph) return null;

  const nodesCount = subgraph.nodes?.length || 0;
  const edgesCount = subgraph.edges?.length || 0;
  const paths = subgraph.paths || [];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div
        className="w-full max-w-6xl h-[88vh] bg-slate-950 border border-indigo-500/30 rounded-3xl shadow-2xl flex flex-col overflow-hidden animate-in zoom-in-95 duration-200"
        role="dialog"
        aria-modal="true"
      >
        {/* Modal Header */}
        <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-900/95 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-blue-600 to-cyan-400 flex items-center justify-center text-white shadow-lg shadow-indigo-600/30">
              <Network className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm sm:text-base font-bold text-white tracking-tight">
                  Neo4j Knowledge Graph Traversal Visualizer
                </h3>
                <Badge variant="purple" size="sm">
                  3D / 2D Hologram
                </Badge>
              </div>
              <p className="text-xs text-slate-400 mt-0.5 truncate max-w-xl">
                {queryText ? `Query: "${queryText}"` : "Interactive traversal reasoning graph"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={onClose}
              className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-white transition-colors"
              title="Close (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Body: Visualizer Component */}
        <div className="flex-1 min-h-0 p-3 sm:p-4 bg-slate-950 flex flex-col">
          <TraversedGraphVisualizer
            subgraph={subgraph}
            queryCategory={queryCategory}
            onClose={onClose}
            isModal={true}
          />
        </div>

        {/* Modal Footer: Traversal Paths Summary */}
        <div className="px-5 py-3 border-t border-slate-800 bg-slate-900/80 flex flex-wrap items-center justify-between gap-3 text-xs shrink-0">
          <div className="flex items-center gap-2 text-slate-400">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>
              Traversed {nodesCount} entity nodes &amp; {edgesCount} relationships in Neo4j with
              grounded enterprise security constraints.
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-400">
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500" /> Organization
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" /> Technology
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" /> Project
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500" /> Policy
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
