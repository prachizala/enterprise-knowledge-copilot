"use client";

import React from "react";
import { X, BookOpen, FileText, CheckCircle2, Copy, ExternalLink, ShieldCheck } from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

export interface CitationDetail {
  id: number | string;
  title: string;
  location: string;
  snippet: string;
  document_id?: string;
  chunk_id?: string;
  relevance_score?: number;
}

export interface CitationDrawerProps {
  citation: CitationDetail | null;
  onClose: () => void;
}

export function CitationDrawer({ citation, onClose }: CitationDrawerProps) {
  const [copied, setCopied] = React.useState(false);

  if (!citation) return null;

  const handleCopy = () => {
    navigator.clipboard.writeText(citation.snippet);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col h-full animate-in slide-in-from-right duration-300"
        role="dialog"
        aria-modal="true"
      >
        {/* Header */}
        <div className="p-5 border-b border-slate-800 flex items-center justify-between shrink-0 bg-slate-950/60">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono font-bold text-cyan-400">
                  Citation [{citation.id}]
                </span>
                <Badge variant="success" size="sm">
                  Verified Grounded Source
                </Badge>
              </div>
              <h3 className="text-sm font-semibold text-white truncate max-w-xs mt-0.5" title={citation.title}>
                {citation.title}
              </h3>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Close citation drawer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 flex-1 overflow-y-auto space-y-5">
          {/* Provenance Pill Bar */}
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700 font-mono">
              {citation.location}
            </span>
            {citation.relevance_score !== undefined && (
              <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                Relevance: {(citation.relevance_score * 100).toFixed(1)}%
              </span>
            )}
          </div>

          {/* Quoted Excerpt Box */}
          <div className="space-y-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider block">
              Grounded Source Excerpt:
            </span>
            <div className="p-4 rounded-xl bg-slate-950 border border-cyan-500/30 text-slate-200 text-xs sm:text-sm leading-relaxed font-sans shadow-inner whitespace-pre-wrap selection:bg-cyan-500/30">
              &ldquo;{citation.snippet}&rdquo;
            </div>
          </div>

          {/* Trust & Provenance Checklist */}
          <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-2.5 text-xs text-slate-400">
            <span className="font-semibold text-slate-300 flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              Verifiability & Anti-Hallucination Guard
            </span>
            <p className="text-[11px] leading-relaxed">
              This excerpt was retrieved directly from the immutable enterprise storage layer. Every assertion synthesized by Enterprise Knowledge Copilot is cross-checked against this factual text.
            </p>
          </div>

          {/* Metadata Grid */}
          <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2 text-xs">
            <div className="flex justify-between py-1 border-b border-slate-800/60">
              <span className="text-slate-500">Document Name:</span>
              <span className="text-slate-300 font-medium truncate max-w-[200px]">{citation.title}</span>
            </div>
            {citation.document_id && (
              <div className="flex justify-between py-1 border-b border-slate-800/60 font-mono text-[11px]">
                <span className="text-slate-500 font-sans">Document ID:</span>
                <span className="text-indigo-400">{citation.document_id.slice(0, 12)}...</span>
              </div>
            )}
            {citation.chunk_id && (
              <div className="flex justify-between py-1 font-mono text-[11px]">
                <span className="text-slate-500 font-sans">Chunk ID:</span>
                <span className="text-cyan-400">{citation.chunk_id.slice(0, 12)}...</span>
              </div>
            )}
          </div>
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-slate-800 bg-slate-950/60 flex items-center justify-between gap-3 shrink-0">
          <Button variant="outline" size="sm" onClick={handleCopy} className="text-xs">
            {copied ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
                <span>Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                <span>Copy Snippet</span>
              </>
            )}
          </Button>

          <a href="/documents" className="inline-flex">
            <Button variant="primary" size="sm" className="text-xs">
              <FileText className="w-3.5 h-3.5 mr-1.5" />
              <span>Open Document Center</span>
              <ExternalLink className="w-3 h-3 ml-1" />
            </Button>
          </a>
        </div>
      </div>
    </div>
  );
}
