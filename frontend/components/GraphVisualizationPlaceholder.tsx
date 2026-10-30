import React from "react";
import { Share2, ZoomIn, ZoomOut, Maximize2, Layers, Filter, Info } from "lucide-react";

export function GraphVisualizationPlaceholder() {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm p-6 flex flex-col justify-between shadow-xl">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              <Share2 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Knowledge Graph Explorer</h2>
              <p className="text-xs text-slate-400">Interactive Neo4j Topology &amp; Entity Relationships</p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="px-2.5 py-1 text-xs font-medium rounded-full bg-slate-800 text-slate-400 border border-slate-700">
              Neo4j Standby
            </span>
          </div>
        </div>

        {/* Visual Mock Canvas */}
        <div className="mt-6 relative h-64 sm:h-72 w-full rounded-xl bg-slate-950/70 border border-slate-800/80 overflow-hidden flex flex-col items-center justify-center p-6 text-center">
          {/* Subtle graph background grid */}
          <div
            className="absolute inset-0 opacity-15"
            style={{
              backgroundImage: "radial-gradient(#6366f1 1px, transparent 1px)",
              backgroundSize: "24px 24px",
            }}
          />

          {/* Graphical Node / Edge schematic illustration */}
          <div className="relative z-10 max-w-md mx-auto space-y-3">
            <div className="flex items-center justify-center gap-4 text-xs">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-950/80 border border-indigo-600/40 text-indigo-300 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-indigo-400" />
                <span>Entity (Document)</span>
              </div>
              <div className="h-[1px] w-6 bg-slate-700 border-t border-dashed border-slate-500" />
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-950/80 border border-emerald-600/40 text-emerald-300 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span>Concept (Topic)</span>
              </div>
            </div>

            <div className="flex items-center justify-center gap-4 text-xs pt-1">
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-950/80 border border-cyan-600/40 text-cyan-300 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                <span>Organization</span>
              </div>
              <div className="h-[1px] w-6 bg-slate-700 border-t border-dashed border-slate-500" />
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-purple-950/80 border border-purple-600/40 text-purple-300 shadow-sm">
                <span className="w-2 h-2 rounded-full bg-purple-400" />
                <span>Policy / Rule</span>
              </div>
            </div>

            <div className="pt-4">
              <p className="text-sm font-semibold text-slate-200">
                Knowledge Graph Canvas Placeholder
              </p>
              <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                Interactive graph visualizer (force-directed layout, subgraph inspection, and Cypher path traversal) will be integrated in upcoming steps.
              </p>
            </div>
          </div>

          {/* Floating UI controls mock */}
          <div className="absolute bottom-3 right-3 flex items-center gap-1 p-1 rounded-lg bg-slate-900/90 border border-slate-800 text-slate-500">
            <button disabled className="p-1 hover:text-slate-300 cursor-not-allowed" title="Zoom In">
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button disabled className="p-1 hover:text-slate-300 cursor-not-allowed" title="Zoom Out">
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button disabled className="p-1 hover:text-slate-300 cursor-not-allowed" title="Reset View">
              <Maximize2 className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="absolute top-3 left-3 flex items-center gap-1.5 text-[11px] text-slate-500">
            <Layers className="w-3.5 h-3.5" />
            <span>0 Active Graph Nodes (Step 1 Foundation)</span>
          </div>
        </div>
      </div>

      <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500">
        <span className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-slate-400" />
          <span>Neo4j Bolt Driver configured in backend app/graph</span>
        </span>
        <span className="text-[11px] text-indigo-400/80 font-mono">Port 7474 / 7687</span>
      </div>
    </div>
  );
}
