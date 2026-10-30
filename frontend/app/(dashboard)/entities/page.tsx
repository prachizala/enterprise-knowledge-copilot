"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  searchEntities,
  getEntityRelationships,
  EntityResponse,
  EntityRelationshipsResponse,
  RelationshipResponse,
} from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { ArrowRight, ArrowLeft, Network, FileText, Layers, CheckCircle2, Loader2, Sparkles } from "lucide-react";

// ── Entity type badge ────────────────────────────────────────────────────────

const ENTITY_TYPES = [
  "ALL",
  "PERSON",
  "ORGANIZATION",
  "DEPARTMENT",
  "PROJECT",
  "PRODUCT",
  "LOCATION",
  "POLICY",
  "TECHNOLOGY",
  "DATE",
  "MONEY",
  "EMAIL",
  "PHONE",
  "CONTRACT",
  "ROLE",
  "OTHER",
] as const;

const TYPE_COLORS: Record<string, string> = {
  PERSON: "bg-blue-100 text-blue-800",
  ORGANIZATION: "bg-purple-100 text-purple-800",
  DEPARTMENT: "bg-indigo-100 text-indigo-800",
  PROJECT: "bg-amber-100 text-amber-800",
  PRODUCT: "bg-orange-100 text-orange-800",
  LOCATION: "bg-green-100 text-green-800",
  POLICY: "bg-red-100 text-red-800",
  TECHNOLOGY: "bg-cyan-100 text-cyan-800",
  DATE: "bg-slate-100 text-slate-800",
  MONEY: "bg-emerald-100 text-emerald-800",
  EMAIL: "bg-violet-100 text-violet-800",
  PHONE: "bg-pink-100 text-pink-800",
  CONTRACT: "bg-rose-100 text-rose-800",
  ROLE: "bg-sky-100 text-sky-800",
  OTHER: "bg-gray-100 text-gray-700",
};

function TypeBadge({ type }: { type: string }) {
  const cls = TYPE_COLORS[type] ?? TYPE_COLORS.OTHER;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${cls}`}>
      {type}
    </span>
  );
}

// ── Skeleton loader ──────────────────────────────────────────────────────────

function SkeletonRow() {
  return (
    <tr className="animate-pulse">
      {[1, 2, 3, 4, 5].map((i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-3 bg-gray-200 rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function EntitiesPage() {
  const [entities, setEntities] = useState<EntityResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("ALL");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  // Selected entity for relationship inspection (Section 19)
  const [selectedEntity, setSelectedEntity] = useState<EntityResponse | null>(null);
  const [relationships, setRelationships] = useState<EntityRelationshipsResponse | null>(null);
  const [loadingRel, setLoadingRel] = useState(false);
  const [selectedRelDetail, setSelectedRelDetail] = useState<RelationshipResponse | null>(null);

  // Debounce search input
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 350);
    return () => clearTimeout(t);
  }, [query]);

  const fetchEntities = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const effectiveQuery = debouncedQuery.trim() || "a";
      const result = await searchEntities(effectiveQuery, {
        entity_type: selectedType === "ALL" ? undefined : selectedType,
        page,
        page_size: PAGE_SIZE,
      });
      setEntities(result.entities);
      setTotal(result.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load entities");
      setEntities([]);
    } finally {
      setLoading(false);
    }
  }, [debouncedQuery, selectedType, page]);

  useEffect(() => {
    fetchEntities();
  }, [fetchEntities]);

  // Open entity inspection drawer
  const handleSelectEntity = async (entity: EntityResponse) => {
    setSelectedEntity(entity);
    setSelectedRelDetail(null);
    setLoadingRel(true);
    try {
      const res = await getEntityRelationships(entity.id);
      setRelationships(res);
    } catch {
      setRelationships(null);
    } finally {
      setLoadingRel(false);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Entity & Relationship Explorer</h1>
          <p className="mt-1 text-sm text-gray-500">
            Browse extracted canonical entities and inspect their grounded incoming and outgoing relationships.
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full bg-gray-100 text-gray-700 font-medium">
            {total.toLocaleString()} entities
          </span>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-4">
        {/* Search input */}
        <div className="relative">
          <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
            <svg className="h-4 w-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => { setQuery(e.target.value); setPage(1); }}
            placeholder="Search entities by name…"
            className="pl-9 pr-4 py-2 w-full border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Type filter pills */}
        <div className="flex flex-wrap gap-2">
          {ENTITY_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => { setSelectedType(t); setPage(1); }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                selectedType === t
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Entity table */}
      <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Entity
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Mentions
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Documents
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  First Seen
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Relationships
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {loading
                ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} />)
                : entities.length === 0
                ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-gray-400 text-sm">
                      {error
                        ? `Error: ${error}`
                        : debouncedQuery
                        ? `No entities matching "${debouncedQuery}"`
                        : "No entities found. Upload and process documents to extract entities."}
                    </td>
                  </tr>
                )
                : entities.map((entity) => (
                  <tr
                    key={entity.id}
                    onClick={() => handleSelectEntity(entity)}
                    className="hover:bg-blue-50/50 cursor-pointer transition-colors group"
                  >
                    <td className="px-4 py-3">
                      <div className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                        {entity.display_name}
                      </div>
                      <div className="text-xs text-gray-400 font-mono mt-0.5">{entity.canonical_name}</div>
                    </td>
                    <td className="px-4 py-3">
                      <TypeBadge type={entity.entity_type} />
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700 font-medium">
                      {entity.mention_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">
                      {entity.document_count.toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {entity.created_at
                        ? new Date(entity.created_at).toLocaleDateString()
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="inline-flex items-center gap-1 text-xs text-blue-600 font-medium group-hover:underline">
                        <Network className="w-3.5 h-3.5" />
                        <span>Inspect</span>
                      </span>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between text-sm text-gray-500">
            <span>
              Showing {((page - 1) * PAGE_SIZE) + 1}–{Math.min(page * PAGE_SIZE, total)} of {total.toLocaleString()}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1 border border-gray-200 rounded text-xs hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="px-3 py-1 border border-gray-200 rounded text-xs hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Entity Relationship Inspection Modal (Section 19) */}
      {selectedEntity && (
        <Modal
          isOpen={!!selectedEntity}
          onClose={() => {
            setSelectedEntity(null);
            setSelectedRelDetail(null);
          }}
          title={selectedEntity.display_name}
          description={`Canonical: ${selectedEntity.canonical_name} • ${selectedEntity.mention_count} mentions across ${selectedEntity.document_count} documents`}
          className="max-w-3xl"
        >
          <div className="space-y-4 text-xs">
            {/* Header badges */}
            <div className="flex items-center justify-between p-3 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="flex items-center gap-2">
                <span className="text-slate-400">Type:</span>
                <TypeBadge type={selectedEntity.entity_type} />
              </div>
              <div className="flex items-center gap-4 text-slate-400">
                <span>
                  Outgoing: <strong className="text-slate-200">{relationships?.total_outgoing ?? 0}</strong>
                </span>
                <span>
                  Incoming: <strong className="text-slate-200">{relationships?.total_incoming ?? 0}</strong>
                </span>
              </div>
            </div>

            {loadingRel ? (
              <div className="p-8 text-center text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                <span>Loading entity relationships...</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Outgoing relationships */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-300 text-xs px-1">
                    <ArrowRight className="w-3.5 h-3.5 text-blue-400" />
                    <span>Outgoing Relationships</span>
                  </div>
                  <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                    {relationships && relationships.outgoing.length > 0 ? (
                      relationships.outgoing.map((rel) => (
                        <div
                          key={rel.id}
                          onClick={() => setSelectedRelDetail(rel)}
                          className={`p-2.5 rounded-lg border transition-all cursor-pointer ${
                            selectedRelDetail?.id === rel.id
                              ? "bg-slate-900 border-blue-500 shadow-md"
                              : "bg-slate-950/70 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-1">
                            <span className="px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-300 font-mono text-[10px] font-bold">
                              {rel.relationship_type}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {(rel.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="mt-1 font-medium text-slate-200 truncate">
                            → {rel.target_entity.display_name}
                            <span className="ml-1 text-[10px] text-slate-500">
                              ({rel.target_entity.entity_type})
                            </span>
                          </div>
                          {rel.evidence_text && (
                            <p className="mt-1 text-[10px] text-slate-400 italic line-clamp-2">
                              &ldquo;{rel.evidence_text}&rdquo;
                            </p>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="p-4 text-center text-slate-500 bg-slate-950/40 rounded-lg border border-slate-900">
                        No outgoing relationships found.
                      </div>
                    )}
                  </div>
                </div>

                {/* Incoming relationships */}
                <div className="space-y-2">
                  <div className="flex items-center gap-1.5 font-semibold text-slate-300 text-xs px-1">
                    <ArrowLeft className="w-3.5 h-3.5 text-purple-400" />
                    <span>Incoming Relationships</span>
                  </div>
                  <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                    {relationships && relationships.incoming.length > 0 ? (
                      relationships.incoming.map((rel) => (
                        <div
                          key={rel.id}
                          onClick={() => setSelectedRelDetail(rel)}
                          className={`p-2.5 rounded-lg border transition-all cursor-pointer ${
                            selectedRelDetail?.id === rel.id
                              ? "bg-slate-900 border-purple-500 shadow-md"
                              : "bg-slate-950/70 border-slate-800 hover:border-slate-700"
                          }`}
                        >
                          <div className="flex items-center justify-between gap-1">
                            <span className="px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-300 font-mono text-[10px] font-bold">
                              {rel.relationship_type}
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">
                              {(rel.confidence * 100).toFixed(0)}%
                            </span>
                          </div>
                          <div className="mt-1 font-medium text-slate-200 truncate">
                            ← {rel.source_entity.display_name}
                            <span className="ml-1 text-[10px] text-slate-500">
                              ({rel.source_entity.entity_type})
                            </span>
                          </div>
                          {rel.evidence_text && (
                            <p className="mt-1 text-[10px] text-slate-400 italic line-clamp-2">
                              &ldquo;{rel.evidence_text}&rdquo;
                            </p>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="p-4 text-center text-slate-500 bg-slate-950/40 rounded-lg border border-slate-900">
                        No incoming relationships found.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Grounded Relationship Evidence Details (Section 19) */}
            {selectedRelDetail && (
              <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-700 space-y-2 animate-in fade-in">
                <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-200">
                      {selectedRelDetail.source_entity.display_name}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 font-mono font-bold text-[10px]">
                      {selectedRelDetail.relationship_type}
                    </span>
                    <span className="font-semibold text-slate-200">
                      {selectedRelDetail.target_entity.display_name}
                    </span>
                  </div>
                  <span className="text-emerald-400 font-mono text-[10px]">
                    Confidence: {(selectedRelDetail.confidence * 100).toFixed(1)}%
                  </span>
                </div>

                {selectedRelDetail.evidence_text && (
                  <div>
                    <span className="text-[10px] text-slate-500 block">Source Evidence:</span>
                    <p className="p-2 rounded bg-slate-950 text-slate-300 italic font-sans border border-slate-800/80">
                      &ldquo;{selectedRelDetail.evidence_text}&rdquo;
                    </p>
                  </div>
                )}

                <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 font-mono pt-1">
                  <span>Document ID: {selectedRelDetail.document_id}</span>
                  <span>Chunk ID: {selectedRelDetail.chunk_id}</span>
                  {selectedRelDetail.model && <span>Model: {selectedRelDetail.model}</span>}
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}

      {/* Info note */}
      <p className="text-xs text-gray-400">
        Entities and relationships are extracted from document chunks and linked through grounded source evidence.
        Click any entity above to inspect its incoming and outgoing connections.
      </p>
    </div>
  );
}
