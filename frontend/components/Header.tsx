import React from "react";
import { Network, Database, ShieldCheck, Cpu } from "lucide-react";

export function Header() {
  return (
    <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-indigo-600 to-blue-500 text-white shadow-lg shadow-indigo-500/20">
              <Network className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold tracking-tight text-white">
                  Enterprise Knowledge Copilot
                </h1>
                <span className="px-2 py-0.5 text-xs font-medium rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Step 1: Foundation
                </span>
              </div>
              <p className="text-sm font-medium text-slate-400">
                Knowledge Graph RAG for Enterprise Data
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4 text-xs text-slate-400">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>FastAPI Ready</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <Database className="w-3.5 h-3.5 text-cyan-400" />
              <span>PostgreSQL & Neo4j Spec</span>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
              <Cpu className="w-3.5 h-3.5 text-purple-400" />
              <span>Hybrid RAG Spec</span>
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
