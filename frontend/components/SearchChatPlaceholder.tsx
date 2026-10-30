import React from "react";
import { Search, Sparkles, MessageSquare, ArrowRight, CornerDownLeft, Lock } from "lucide-react";

export function SearchChatPlaceholder() {
  return (
    <div className="rounded-2xl border border-slate-800/80 bg-slate-900/40 backdrop-blur-sm p-6 flex flex-col justify-between shadow-xl">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <MessageSquare className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Enterprise Search & Copilot</h2>
              <p className="text-xs text-slate-400">Hybrid Graph + Vector Retrieval Interface</p>
            </div>
          </div>
          <span className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/20">
            <Lock className="w-3 h-3" />
            Placeholder (Step 1)
          </span>
        </div>

        {/* Informative placeholder state */}
        <div className="mt-6 space-y-4">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-sm text-slate-300">
            <div className="flex items-center gap-2 text-indigo-400 font-medium mb-1">
              <Sparkles className="w-4 h-4" />
              <span>Future Feature Preview: Hybrid GraphRAG Querying</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              In subsequent steps, this copilot interface will enable grounded enterprise Q&amp;A. Queries will simultaneously traverse the Neo4j Knowledge Graph for relational context and PostgreSQL/Vector stores for semantic matching, delivering answers with verified source citations.
            </p>
          </div>

          {/* Sample query pill suggestions */}
          <div className="space-y-2">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-500">
              Target Enterprise Query Capabilities (Planned):
            </p>
            <div className="flex flex-wrap gap-2 text-xs">
              <span className="px-3 py-1.5 rounded-lg bg-slate-800/50 text-slate-400 border border-slate-700/40">
                &ldquo;What regulatory compliance guidelines apply to Q3 data retention?&rdquo;
              </span>
              <span className="px-3 py-1.5 rounded-lg bg-slate-800/50 text-slate-400 border border-slate-700/40">
                &ldquo;Show dependencies between Project Titan and Vendor contracts&rdquo;
              </span>
              <span className="px-3 py-1.5 rounded-lg bg-slate-800/50 text-slate-400 border border-slate-700/40">
                &ldquo;Summarize security incident policies with source citations&rdquo;
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Disabled search input placeholder */}
      <div className="mt-8 pt-4 border-t border-slate-800/80">
        <div className="relative">
          <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
            <Search className="w-4 h-4" />
          </div>
          <input
            type="text"
            disabled
            placeholder="Search enterprise knowledge base or ask a question... (Enabled in future steps)"
            className="w-full pl-10 pr-24 py-3 bg-slate-950/70 border border-slate-800 rounded-xl text-xs sm:text-sm text-slate-400 placeholder-slate-600 focus:outline-none cursor-not-allowed"
          />
          <div className="absolute inset-y-0 right-1.5 flex items-center">
            <button
              disabled
              className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-slate-800 text-slate-500 text-xs font-medium cursor-not-allowed border border-slate-700/50"
            >
              <span>Submit</span>
              <CornerDownLeft className="w-3 h-3" />
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] text-slate-500">
          Chat &amp; RAG generation are inactive in Step 1. Backend API foundation is running on port 8000.
        </p>
      </div>
    </div>
  );
}
