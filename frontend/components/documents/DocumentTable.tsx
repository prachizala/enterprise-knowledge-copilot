"use client";

import React, { useState, useMemo } from "react";
import { RecentDocumentItem } from "@/lib/demo-data";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import {
  FileText,
  Eye,
  Download,
  Trash2,
  Clock,
  BookOpen,
  Loader2,
  RefreshCw,
  AlertCircle,
  FileCheck,
  Layers,
  Hash,
  Search,
  CheckCircle2,
  Sparkles,
  Network,
  ArrowRight,
} from "lucide-react";
import {
  getDocumentContent,
  getDocumentChunks,
  getDownloadUrl,
  processDocument,
  generateDocumentEmbeddings,
  extractDocumentEntities,
  extractDocumentRelationships,
  listDocumentRelationships,
  triggerFullPipeline,
  DocumentContentResponse,
  DocumentChunkResponse,
  RelationshipResponse,
} from "@/lib/api";

export interface DocumentTableProps {
  documents: RecentDocumentItem[];
  onDeleteDocument?: (id: string) => void;
  onDocumentUpdated?: () => void;
}

export function DocumentTable({
  documents,
  onDeleteDocument,
  onDocumentUpdated,
}: DocumentTableProps) {
  const [selectedDoc, setSelectedDoc] = useState<RecentDocumentItem | null>(null);
  const [extractedContent, setExtractedContent] = useState<DocumentContentResponse | null>(null);
  const [loadingContent, setLoadingContent] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);

  // Step 5 Chunks State
  const [chunksList, setChunksList] = useState<DocumentChunkResponse[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [chunksError, setChunksError] = useState<string | null>(null);
  const [chunkSearch, setChunkSearch] = useState("");
  const [chunkPageFilter, setChunkPageFilter] = useState("all");

  const [isReprocessing, setIsReprocessing] = useState(false);
  const [isGeneratingEmbeddings, setIsGeneratingEmbeddings] = useState(false);
  const [isExtractingEntities, setIsExtractingEntities] = useState(false);
  const [isExtractingRelationships, setIsExtractingRelationships] = useState(false);
  const [docRelationships, setDocRelationships] = useState<RelationshipResponse[]>([]);
  const [loadingRelationships, setLoadingRelationships] = useState(false);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"details" | "text" | "chunks" | "relationships">("details");

  const fetchDocRelationships = async (docId: string) => {
    setLoadingRelationships(true);
    try {
      const res = await listDocumentRelationships(docId);
      setDocRelationships(res.relationships || []);
    } catch {
      setDocRelationships([]);
    } finally {
      setLoadingRelationships(false);
    }
  };

  // Open Document Details modal and fetch extracted text content & chunks
  const handleOpenDocModal = async (doc: RecentDocumentItem) => {
    setSelectedDoc(doc);
    setActiveTab("details");
    setExtractedContent(null);
    setContentError(null);
    setChunksList([]);
    setChunksError(null);
    setDocRelationships([]);
    setChunkSearch("");
    setChunkPageFilter("all");

    // Fetch text content
    setLoadingContent(true);
    try {
      const content = await getDocumentContent(doc.id);
      setExtractedContent(content);
    } catch (err: any) {
      setContentError(err.message || "Extracted text content not available.");
    } finally {
      setLoadingContent(false);
    }

    // Fetch discrete chunks
    setLoadingChunks(true);
    try {
      const chunkData = await getDocumentChunks(doc.id, 0, 100);
      setChunksList(chunkData.chunks || []);
    } catch (err: any) {
      setChunksError(err.message || "Document chunks not available.");
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleDownload = (doc: RecentDocumentItem) => {
    const url = getDownloadUrl(doc.id);
    window.open(url, "_blank");
    setActionNotice(`Initiated download for "${doc.name}"`);
    setTimeout(() => setActionNotice(null), 3000);
  };

  const handleReprocess = async (doc: RecentDocumentItem) => {
    setIsReprocessing(true);
    setActionNotice(`Reprocessing extraction and chunking for "${doc.name}"...`);
    try {
      const updated = await processDocument(doc.id);
      setActionNotice(`Successfully reprocessed and indexed "${doc.name}"`);
      // Update modal document state
      setSelectedDoc((prev) =>
        prev
          ? {
              ...prev,
              status: updated.status === "processed" ? "Processed" : "Failed",
              extraction_status: updated.extraction_status,
              extracted_characters: updated.extracted_text_length,
              chunks: updated.total_chunks !== undefined ? updated.total_chunks : prev.chunks,
              processed_at: updated.processed_at,
              processing_error: updated.processing_error,
            }
          : null
      );
      // Refresh content
      const content = await getDocumentContent(doc.id);
      setExtractedContent(content);
      setContentError(null);

      // Refresh chunks
      const chunkData = await getDocumentChunks(doc.id, 0, 100);
      setChunksList(chunkData.chunks || []);
      setChunksError(null);

      if (onDocumentUpdated) onDocumentUpdated();
    } catch (err: any) {
      setActionNotice(`Reprocessing failed: ${err.message}`);
    } finally {
      setIsReprocessing(false);
      setTimeout(() => setActionNotice(null), 3500);
    }
  };

  const handleGenerateEmbeddings = async (doc: RecentDocumentItem) => {
    setIsGeneratingEmbeddings(true);
    setActionNotice(`Generating embeddings for "${doc.name}"...`);
    try {
      const res = await generateDocumentEmbeddings(doc.id, true);
      setActionNotice(
        `Generated ${res.embedded_chunks} embeddings using ${res.model}`
      );
      if (onDocumentUpdated) onDocumentUpdated();
      if (selectedDoc && selectedDoc.id === doc.id) {
        setSelectedDoc((prev) =>
          prev
            ? {
                ...prev,
                embedding_status: "completed",
                embedded_chunks: res.embedded_chunks,
                embedding_model: res.model,
              }
            : null
        );
      }
    } catch (err: any) {
      setActionNotice(`Embedding generation failed: ${err.message}`);
    } finally {
      setIsGeneratingEmbeddings(false);
      setTimeout(() => setActionNotice(null), 3500);
    }
  };

  const handleExtractEntities = async (doc: RecentDocumentItem) => {
    setIsExtractingEntities(true);
    setActionNotice(`Extracting entities from "${doc.name}"...`);
    try {
      const res = await extractDocumentEntities(doc.id, false);
      setActionNotice(res.message || "Entity extraction complete.");
      if (onDocumentUpdated) onDocumentUpdated();
      if (selectedDoc && selectedDoc.id === doc.id) {
        setSelectedDoc((prev) =>
          prev ? { ...prev, entity_extraction_status: "completed" } : null
        );
      }
    } catch (err: any) {
      setActionNotice(`Entity extraction failed: ${err.message}`);
    } finally {
      setIsExtractingEntities(false);
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  const handleExtractRelationships = async (doc: RecentDocumentItem) => {
    setIsExtractingRelationships(true);
    setActionNotice(`Extracting relationships from "${doc.name}"...`);
    try {
      const res = await extractDocumentRelationships(doc.id, false);
      setActionNotice(res.message || "Relationship extraction complete.");
      if (onDocumentUpdated) onDocumentUpdated();
      await fetchDocRelationships(doc.id);
      if (selectedDoc && selectedDoc.id === doc.id) {
        setSelectedDoc((prev) =>
          prev
            ? {
                ...prev,
                relationship_extraction_status: "completed",
                relationship_count:
                  res.stats?.relationships_created ?? prev.relationship_count,
              }
            : null
        );
      }
    } catch (err: any) {
      setActionNotice(`Relationship extraction failed: ${err.message}`);
    } finally {
      setIsExtractingRelationships(false);
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  const handleRunFullPipeline = async (doc: RecentDocumentItem) => {
    setIsReprocessing(true);
    setActionNotice(`Triggering end-to-end ingestion pipeline (6 stages) for "${doc.name}"...`);
    try {
      const job = await triggerFullPipeline(doc.id, true);
      setActionNotice(
        `Pipeline job started: ${job.status.toUpperCase()} (${job.current_step || "Stage 1"}). Neo4j sync initiated.`
      );
      if (onDocumentUpdated) onDocumentUpdated();
    } catch (err: any) {
      setActionNotice(`Pipeline trigger failed: ${err.message}`);
    } finally {
      setIsReprocessing(false);
      setTimeout(() => setActionNotice(null), 4000);
    }
  };

  const handleDelete = async (doc: RecentDocumentItem) => {
    if (confirm(`Delete ${doc.name} and all its stored files, text, and chunks?`)) {
      if (onDeleteDocument) onDeleteDocument(doc.id);
      setActionNotice(`Deleted ${doc.name}`);
      setTimeout(() => setActionNotice(null), 2500);
      if (selectedDoc?.id === doc.id) {
        setSelectedDoc(null);
      }
    }
  };

  // Derive distinct page numbers for chunk page filter
  const availablePages = useMemo(() => {
    const pages = new Set<number>();
    chunksList.forEach((c) => {
      if (c.page_number) pages.add(c.page_number);
    });
    return Array.from(pages).sort((a, b) => a - b);
  }, [chunksList]);

  // Filter chunks by keyword and page number
  const filteredChunks = useMemo(() => {
    return chunksList.filter((c) => {
      const matchesSearch =
        !chunkSearch.trim() ||
        c.content.toLowerCase().includes(chunkSearch.toLowerCase()) ||
        (c.section_header && c.section_header.toLowerCase().includes(chunkSearch.toLowerCase()));

      const matchesPage =
        chunkPageFilter === "all" ||
        (c.page_number !== null && c.page_number !== undefined && c.page_number.toString() === chunkPageFilter);

      return matchesSearch && matchesPage;
    });
  }, [chunksList, chunkSearch, chunkPageFilter]);

  return (
    <>
      {/* Toast Notice */}
      {actionNotice && (
        <div className="mb-4 p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 flex items-center justify-between animate-in fade-in">
          <span>{actionNotice}</span>
          <span className="text-[10px] text-slate-500 font-mono">Document Management</span>
        </div>
      )}

      <div className="rounded-2xl border border-slate-800 bg-slate-900/50 backdrop-blur-sm shadow-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 font-semibold uppercase tracking-wider text-[10px]">
                <th className="py-3 px-4">Document</th>
                <th className="py-3 px-3">Type</th>
                <th className="py-3 px-3">Department</th>
                <th className="py-3 px-3 text-right">Chars</th>
                <th className="py-3 px-3 text-right">Chunks</th>
                <th className="py-3 px-3 text-center">Vectors</th>
                <th className="py-3 px-3 text-center">Entities</th>
                <th className="py-3 px-3 text-center">Relationships</th>
                <th className="py-3 px-3 text-center">Status</th>
                <th className="py-3 px-3">Date</th>
                <th className="py-3 pr-6 pl-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-sans">
              {documents.map((doc) => (
                <tr
                  key={doc.id}
                  onClick={() => handleOpenDocModal(doc)}
                  className="hover:bg-slate-800/40 transition-colors cursor-pointer group"
                >
                  {/* Document Name & Owner */}
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                        <FileText className="w-4 h-4" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-semibold text-slate-200 group-hover:text-white transition-colors truncate max-w-[200px] sm:max-w-xs">
                          {doc.name}
                        </p>
                        <p className="text-[10px] text-slate-400">
                          {doc.owner} • {doc.size}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* Type */}
                  <td className="py-3.5 px-3">
                    <span className="font-mono text-[10px] px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300 font-semibold">
                      {doc.type}
                    </span>
                  </td>

                  {/* Department */}
                  <td className="py-3.5 px-3 text-slate-400">
                    <span className="px-2 py-0.5 rounded-md bg-slate-800/80 border border-slate-700/50 text-[11px]">
                      {doc.department}
                    </span>
                  </td>

                  {/* Extracted Chars */}
                  <td className="py-3.5 px-3 text-right font-mono text-slate-300">
                    {doc.extracted_characters !== undefined
                      ? doc.extracted_characters.toLocaleString()
                      : "0"}
                  </td>

                  {/* Discrete Chunks */}
                  <td className="py-3.5 px-3 text-right font-mono">
                    <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 font-semibold text-[11px]">
                      {doc.chunks !== undefined ? doc.chunks.toLocaleString() : "0"}
                    </span>
                  </td>

                  {/* Vectors (pgvector) */}
                  <td className="py-3.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    {doc.embedding_status === "completed" ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-medium text-[10px]"
                        title={`Embedded with ${doc.embedding_model || "pgvector"}`}
                      >
                        <Sparkles className="w-3 h-3 text-emerald-400" />
                        <span>{doc.embedded_chunks ?? doc.chunks ?? 0}</span>
                      </span>
                    ) : doc.embedding_status === "processing" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-medium text-[10px]">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Embedding</span>
                      </span>
                    ) : doc.embedding_status === "failed" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 font-medium text-[10px]">
                        <AlertCircle className="w-3 h-3" />
                        <span>Failed</span>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleGenerateEmbeddings(doc)}
                        disabled={isGeneratingEmbeddings}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 hover:bg-indigo-600/30 border border-slate-700 hover:border-indigo-500/40 text-slate-400 hover:text-indigo-300 font-medium text-[10px] transition-colors"
                        title="Generate pgvector semantic embeddings"
                      >
                        <Sparkles className="w-3 h-3 text-indigo-400" />
                        <span>Embed</span>
                      </button>
                    )}
                  </td>

                  {/* Entities */}
                  <td className="py-3.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    {doc.entity_extraction_status === "completed" ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-500/10 border border-violet-500/20 text-violet-400 font-medium text-[10px]"
                        title={`${doc.entity_mention_count ?? 0} mentions, ${doc.unique_entity_count ?? 0} unique`}
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        <span>{doc.unique_entity_count ?? doc.entities ?? 0}</span>
                      </span>
                    ) : doc.entity_extraction_status === "processing" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-medium text-[10px]">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Extracting</span>
                      </span>
                    ) : doc.entity_extraction_status === "partial" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 font-medium text-[10px]">
                        <AlertCircle className="w-3 h-3" />
                        <span>Partial</span>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleExtractEntities(doc)}
                        disabled={isExtractingEntities}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 hover:bg-violet-600/30 border border-slate-700 hover:border-violet-500/40 text-slate-400 hover:text-violet-300 font-medium text-[10px] transition-colors"
                        title="Extract named entities"
                      >
                        <Hash className="w-3 h-3 text-violet-400" />
                        <span>Extract</span>
                      </button>
                    )}
                  </td>

                  {/* Relationships */}
                  <td className="py-3.5 px-3 text-center" onClick={(e) => e.stopPropagation()}>
                    {doc.relationship_extraction_status === "completed" ? (
                      <span
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 font-medium text-[10px]"
                        title={`${doc.relationship_count ?? 0} relationships extracted`}
                      >
                        <Network className="w-3 h-3" />
                        <span>{doc.relationship_count ?? 0}</span>
                      </span>
                    ) : doc.relationship_extraction_status === "processing" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-300 font-medium text-[10px]">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        <span>Extracting</span>
                      </span>
                    ) : doc.relationship_extraction_status === "partial" ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-300 font-medium text-[10px]">
                        <AlertCircle className="w-3 h-3" />
                        <span>Partial</span>
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleExtractRelationships(doc)}
                        disabled={isExtractingRelationships}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-800 hover:bg-cyan-600/30 border border-slate-700 hover:border-cyan-500/40 text-slate-400 hover:text-cyan-300 font-medium text-[10px] transition-colors"
                        title="Extract grounded relationships"
                      >
                        <Network className="w-3 h-3 text-cyan-400" />
                        <span>Extract</span>
                      </button>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3.5 px-3 text-center">
                    <Badge
                      variant={
                        doc.status === "Processed"
                          ? "success"
                          : doc.status === "Processing"
                          ? "warning"
                          : doc.status === "Uploaded"
                          ? "info"
                          : "danger"
                      }
                      size="sm"
                    >
                      {doc.status}
                    </Badge>
                  </td>

                  {/* Updated */}
                  <td className="py-3.5 px-3 text-slate-400 whitespace-nowrap">
                    <span className="flex items-center gap-1 text-[11px]">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {doc.updated}
                    </span>
                  </td>

                  {/* Actions */}
                  <td
                    className="py-3.5 pr-6 pl-3 text-right"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleGenerateEmbeddings(doc)}
                        disabled={isGeneratingEmbeddings}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                        title="Generate / Refresh embeddings"
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleOpenDocModal(doc)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="View details & chunks"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDownload(doc)}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                        title="Download original file"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={() => handleDelete(doc)}
                        className="p-1.5 rounded-lg text-rose-400/70 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
                        title="Delete document"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Details & Chunk Inspection Modal */}
      {selectedDoc && (
        <Modal
          isOpen={!!selectedDoc}
          onClose={() => setSelectedDoc(null)}
          title={selectedDoc.name}
          description="Document Metadata, Extracted Text & Structure-Aware Chunks"
          className="max-w-4xl"
        >
          <div className="space-y-4 text-xs">
            {/* Top Action & Navigation Buttons */}
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-950/80 border border-slate-800">
              <div className="flex flex-wrap items-center gap-1 bg-slate-900 p-0.5 rounded-lg border border-slate-800">
                <button
                  type="button"
                  onClick={() => setActiveTab("details")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                    activeTab === "details"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  Metadata Details
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("text")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    activeTab === "text"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  View Text
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("chunks")}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    activeTab === "chunks"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 text-indigo-300" />
                  <span>Chunks ({chunksList.length || selectedDoc.chunks || 0})</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setActiveTab("relationships");
                    fetchDocRelationships(selectedDoc.id);
                  }}
                  className={`px-3 py-1 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    activeTab === "relationships"
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  <Network className="w-3.5 h-3.5 text-cyan-300" />
                  <span>
                    Relationships ({docRelationships.length || selectedDoc.relationship_count || 0})
                  </span>
                </button>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExtractRelationships(selectedDoc)}
                  disabled={isExtractingRelationships || isReprocessing}
                  title="Extract typed relationships between entities"
                >
                  <Network
                    className={`w-3.5 h-3.5 mr-1.5 ${
                      isExtractingRelationships
                        ? "animate-spin text-cyan-400"
                        : "text-cyan-400"
                    }`}
                  />
                  <span>
                    {isExtractingRelationships ? "Extracting..." : "Extract Relationships"}
                  </span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleGenerateEmbeddings(selectedDoc)}
                  disabled={isGeneratingEmbeddings || isReprocessing}
                  title="Generate or refresh dense vector embeddings in PostgreSQL"
                >
                  <Sparkles
                    className={`w-3.5 h-3.5 mr-1.5 ${
                      isGeneratingEmbeddings
                        ? "animate-spin text-emerald-400"
                        : "text-emerald-400"
                    }`}
                  />
                  <span>
                    {isGeneratingEmbeddings ? "Embedding..." : "Embed Vectors"}
                  </span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleReprocess(selectedDoc)}
                  disabled={isReprocessing || isGeneratingEmbeddings}
                  title="Re-run text extraction & chunking pipeline"
                >
                  <RefreshCw
                    className={`w-3.5 h-3.5 mr-1.5 ${
                      isReprocessing ? "animate-spin text-indigo-400" : ""
                    }`}
                  />
                  <span>Reprocess</span>
                </Button>

                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => handleRunFullPipeline(selectedDoc)}
                  disabled={isReprocessing}
                  title="Execute complete 6-stage ingestion pipeline into PostgreSQL and Neo4j"
                  className="bg-indigo-600 hover:bg-indigo-500 text-white"
                >
                  <Layers className={`w-3.5 h-3.5 mr-1.5 ${isReprocessing ? "animate-spin" : ""}`} />
                  <span>Run Full Pipeline</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleDownload(selectedDoc)}
                  title="Download original uploaded file"
                >
                  <Download className="w-3.5 h-3.5 mr-1.5" />
                  <span>Download</span>
                </Button>
              </div>
            </div>

            {/* Tab 1: Detailed Metadata Grid */}
            {activeTab === "details" && (
              <div className="space-y-3">
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3.5 rounded-xl bg-slate-950/70 border border-slate-800">
                  <div>
                    <span className="text-slate-500 text-[11px] block">Document Name:</span>
                    <p className="font-semibold text-slate-200 truncate mt-0.5" title={selectedDoc.name}>
                      {selectedDoc.name}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Type / Format:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">{selectedDoc.type}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Department:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">{selectedDoc.department}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Owner:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">{selectedDoc.owner}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Version:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">{selectedDoc.version || "1.0"}</p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Status:</span>
                    <div className="mt-0.5">
                      <Badge
                        variant={
                          selectedDoc.status === "Processed"
                            ? "success"
                            : selectedDoc.status === "Processing"
                            ? "warning"
                            : selectedDoc.status === "Uploaded"
                            ? "info"
                            : "danger"
                        }
                        size="sm"
                      >
                        {selectedDoc.status}
                      </Badge>
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Uploaded:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">
                      {selectedDoc.created_at
                        ? new Date(selectedDoc.created_at).toLocaleString()
                        : selectedDoc.updated}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Processed:</span>
                    <p className="font-semibold text-slate-200 mt-0.5">
                      {selectedDoc.processed_at
                        ? new Date(selectedDoc.processed_at).toLocaleString()
                        : selectedDoc.extraction_status === "completed"
                        ? "Completed"
                        : selectedDoc.extraction_status || "Pending"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Total Discrete Chunks:</span>
                    <p className="font-semibold text-indigo-400 font-mono mt-0.5">
                      {chunksList.length > 0
                        ? chunksList.length.toLocaleString()
                        : selectedDoc.chunks !== undefined
                        ? selectedDoc.chunks.toLocaleString()
                        : "0"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Extracted Characters:</span>
                    <p className="font-semibold text-indigo-400 font-mono mt-0.5">
                      {extractedContent?.character_count !== undefined
                        ? extractedContent.character_count.toLocaleString()
                        : selectedDoc.extracted_characters !== undefined
                        ? selectedDoc.extracted_characters.toLocaleString()
                        : "0"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Extracted Words:</span>
                    <p className="font-semibold text-indigo-400 font-mono mt-0.5">
                      {extractedContent?.word_count !== undefined
                        ? extractedContent.word_count.toLocaleString()
                        : selectedDoc.extracted_words !== undefined
                        ? selectedDoc.extracted_words.toLocaleString()
                        : "0"}
                    </p>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Vectors (pgvector):</span>
                    <div className="mt-0.5 flex items-center gap-1.5">
                      <span className="font-semibold text-emerald-400 font-mono">
                        {selectedDoc.embedded_chunks ?? (selectedDoc.embedding_status === "completed" ? (selectedDoc.chunks || 0) : 0)} / {selectedDoc.chunks || 0}
                      </span>
                      <span className="text-[10px] text-slate-500">
                        ({selectedDoc.embedding_status || "not_started"})
                      </span>
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500 text-[11px] block">Embedding Model:</span>
                    <p
                      className="font-mono text-slate-300 text-[11px] mt-0.5 truncate"
                      title={selectedDoc.embedding_model || "text-embedding-3-small"}
                    >
                      {selectedDoc.embedding_model || "text-embedding-3-small"}
                    </p>
                  </div>
                  {extractedContent?.page_count && (
                    <div>
                      <span className="text-slate-500 text-[11px] block">Page Count:</span>
                      <p className="font-semibold text-slate-200 mt-0.5">
                        {extractedContent.page_count} pages
                      </p>
                    </div>
                  )}
                </div>

                {selectedDoc.processing_error && (
                  <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-semibold">Extraction Notice: </span>
                      <span>{selectedDoc.processing_error}</span>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Tab 2: Full Extracted Text View */}
            {activeTab === "text" && (
              <div className="space-y-2">
                <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                  <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                    <FileCheck className="w-3.5 h-3.5 text-emerald-400" />
                    Plain Structured Text Content
                  </span>
                  {extractedContent && (
                    <span className="text-[11px] font-mono text-slate-400">
                      {extractedContent.character_count.toLocaleString()} chars •{" "}
                      {extractedContent.word_count.toLocaleString()} words
                    </span>
                  )}
                </div>

                {loadingContent ? (
                  <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center gap-2 bg-slate-950/60 rounded-xl border border-slate-800">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                    <span>Loading extracted text from storage...</span>
                  </div>
                ) : extractedContent ? (
                  <div className="max-h-80 overflow-y-auto p-4 rounded-xl bg-slate-950 font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap border border-slate-800 shadow-inner">
                    {extractedContent.text}
                  </div>
                ) : (
                  <div className="p-6 text-center text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800">
                    <p className="text-xs">{contentError || "No extracted content available."}</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      Click the &ldquo;Reprocess&rdquo; button above to trigger text extraction on this document.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 3: Structure-Aware Chunks Inspection */}
            {activeTab === "chunks" && (
              <div className="space-y-3">
                {/* Search & Filter Bar */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
                  <div className="flex items-center gap-2 flex-1">
                    <div className="relative flex-1 max-w-xs">
                      <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="text"
                        placeholder="Search within chunks..."
                        value={chunkSearch}
                        onChange={(e) => setChunkSearch(e.target.value)}
                        className="w-full bg-slate-900 border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
                      />
                    </div>

                    {availablePages.length > 0 && (
                      <select
                        value={chunkPageFilter}
                        onChange={(e) => setChunkPageFilter(e.target.value)}
                        aria-label="Filter chunks by page"
                        className="bg-slate-900 border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="all">All Pages ({availablePages.length})</option>
                        {availablePages.map((p) => (
                          <option key={p} value={p.toString()}>
                            Page {p}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div className="flex items-center gap-2 text-[11px] text-slate-400">
                    <span className="font-mono text-indigo-400 font-semibold">
                      {filteredChunks.length} of {chunksList.length} chunks
                    </span>
                    {chunksList.length > 0 && (
                      <span className="text-slate-600 hidden sm:inline">
                        • Avg ~{Math.round(chunksList.reduce((acc, c) => acc + c.token_count, 0) / chunksList.length)} tokens
                      </span>
                    )}
                  </div>
                </div>

                {/* Chunks List */}
                {loadingChunks ? (
                  <div className="p-8 text-center text-slate-400 flex flex-col items-center justify-center gap-2 bg-slate-950/60 rounded-xl border border-slate-800">
                    <Loader2 className="w-5 h-5 animate-spin text-indigo-400" />
                    <span>Loading discrete chunks from database...</span>
                  </div>
                ) : filteredChunks.length > 0 ? (
                  <div className="max-h-96 overflow-y-auto space-y-2.5 pr-1">
                    {filteredChunks.map((chunk) => (
                      <div
                        key={chunk.id || `chunk-${chunk.chunk_index}`}
                        className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-slate-700 transition-colors space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-300 font-mono text-[11px] font-semibold flex items-center gap-1">
                              <Hash className="w-3 h-3 text-indigo-400" />
                              Chunk #{chunk.chunk_index + 1}
                            </span>

                            {chunk.page_number && (
                              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">
                                Page {chunk.page_number}
                              </span>
                            )}

                            {chunk.section_header && (
                              <span
                                className="text-slate-300 font-medium text-[11px] flex items-center gap-1 truncate max-w-xs"
                                title={chunk.section_header}
                              >
                                <span className="text-slate-500">§</span>
                                {chunk.section_header}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center gap-2 text-[10px] font-mono text-slate-400">
                            {chunk.content_hash && (
                              <span
                                className="px-1.5 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-500 font-mono text-[9px]"
                                title={`Content SHA-256: ${chunk.content_hash}`}
                              >
                                sha: {chunk.content_hash.slice(0, 8)}...
                              </span>
                            )}
                            <span>{chunk.token_count} tokens</span>
                            <span>•</span>
                            <span>{chunk.char_count} chars</span>
                          </div>
                        </div>

                        {/* Chunk text content */}
                        <div className="font-mono text-[11px] leading-relaxed text-slate-300 whitespace-pre-wrap bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                          {chunk.content}
                        </div>

                        {/* Metadata Pills */}
                        {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                          <div className="flex flex-wrap items-center gap-1.5 pt-1">
                            {chunk.metadata.source_format && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800/60 text-slate-400 font-mono">
                                format: {chunk.metadata.source_format}
                              </span>
                            )}
                            {chunk.metadata.is_table && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono flex items-center gap-1">
                                <CheckCircle2 className="w-3 h-3" />
                                table: true
                              </span>
                            )}
                            {chunk.metadata.is_record_group && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/10 border border-amber-500/20 text-amber-400 font-mono">
                                records:{" "}
                                {chunk.metadata.record_range
                                  ? `${chunk.metadata.record_range[0]}-${chunk.metadata.record_range[1]}`
                                  : "grouped"}
                              </span>
                            )}
                            {chunk.metadata.heading_level && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 border border-purple-500/20 text-purple-400 font-mono">
                                H{chunk.metadata.heading_level}
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-6 text-center text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800">
                    <p className="text-xs">{chunksError || "No discrete chunks found."}</p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {chunkSearch
                        ? "No chunks matched your search criteria."
                        : "Click 'Reprocess' above to execute structure-aware chunking for this document."}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Tab 4: Extracted Relationships */}
            {activeTab === "relationships" && (
              <div className="space-y-3">
                <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
                  <span className="text-slate-400 text-xs">
                    Total Relationships:{" "}
                    <strong className="text-slate-200">
                      {docRelationships.length || selectedDoc.relationship_count || 0}
                    </strong>
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => fetchDocRelationships(selectedDoc.id)}
                    disabled={loadingRelationships}
                  >
                    <RefreshCw className={`w-3 h-3 mr-1 ${loadingRelationships ? "animate-spin" : ""}`} />
                    <span>Refresh</span>
                  </Button>
                </div>

                {loadingRelationships ? (
                  <div className="p-8 text-center text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800 flex items-center justify-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin text-cyan-400" />
                    <span>Loading extracted relationships...</span>
                  </div>
                ) : docRelationships.length > 0 ? (
                  <div className="space-y-2 max-h-[460px] overflow-y-auto pr-1">
                    {docRelationships.map((rel) => (
                      <div
                        key={rel.id}
                        className="p-3 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-colors space-y-2"
                      >
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          {/* Source -> Type -> Target */}
                          <div className="flex items-center gap-2 flex-wrap font-medium text-xs">
                            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200">
                              {rel.source_entity.display_name}
                              <span className="ml-1 text-[10px] text-slate-400 font-normal">
                                ({rel.source_entity.entity_type})
                              </span>
                            </span>
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20 text-cyan-300 font-mono text-[11px] font-semibold">
                              <ArrowRight className="w-3 h-3 text-cyan-400" />
                              {rel.relationship_type}
                            </span>
                            <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200">
                              {rel.target_entity.display_name}
                              <span className="ml-1 text-[10px] text-slate-400 font-normal">
                                ({rel.target_entity.entity_type})
                              </span>
                            </span>
                          </div>

                          {/* Confidence */}
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-emerald-400">
                            {(rel.confidence * 100).toFixed(0)}% conf
                          </span>
                        </div>

                        {/* Grounded Evidence Text */}
                        {rel.evidence_text && (
                          <p className="text-[11px] text-slate-400 bg-slate-900/80 p-2 rounded-lg border border-slate-800/60 italic font-sans">
                            &ldquo;{rel.evidence_text}&rdquo;
                          </p>
                        )}

                        <div className="flex items-center justify-between text-[10px] text-slate-500 font-mono">
                          <span>Chunk: {rel.chunk_id.slice(0, 8)}...</span>
                          {rel.model && <span>Model: {rel.model}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="p-8 text-center text-slate-400 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                    <p className="text-xs font-medium text-slate-300">No relationships extracted yet</p>
                    <p className="text-[11px] text-slate-500 max-w-md mx-auto">
                      {selectedDoc.entities === 0 && selectedDoc.unique_entity_count === 0
                        ? "Entity extraction must be performed before relationships can be extracted."
                        : "Click 'Extract Relationships' to extract typed connections between identified entities."}
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleExtractRelationships(selectedDoc)}
                      disabled={isExtractingRelationships}
                      className="mt-2"
                    >
                      <Network className="w-3.5 h-3.5 mr-1 text-cyan-400" />
                      <span>Extract Relationships Now</span>
                    </Button>
                  </div>
                )}
              </div>
            )}
          </div>
        </Modal>
      )}
    </>
  );
}
