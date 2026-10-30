"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { DocumentUploadModal } from "@/components/documents/DocumentUploadModal";
import { SearchInput } from "@/components/ui/SearchInput";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { RECENT_DOCUMENTS, RecentDocumentItem } from "@/lib/demo-data";
import { listDocuments, deleteDocument, DocumentResponse } from "@/lib/api";
import { Upload, RefreshCw, Database } from "lucide-react";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<RecentDocumentItem[]>(RECENT_DOCUMENTS);
  const [loading, setLoading] = useState(false);
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [search, setSearch] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("All");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const mapAndSetDocs = (docsList: DocumentResponse[]) => {
    const formatted: RecentDocumentItem[] = docsList.map((d) => ({
      id: d.id,
      name: d.filename,
      type: (d.file_type ? d.file_type.toUpperCase() : "TXT") as any,
      department: d.department,
      updated: d.processed_at
        ? new Date(d.processed_at).toLocaleTimeString()
        : new Date(d.created_at).toLocaleDateString(),
      status: (d.status === "processed"
        ? "Processed"
        : d.status === "processing"
        ? "Processing"
        : d.status === "failed"
        ? "Failed"
        : "Uploaded") as any,
      owner: d.owner,
      chunks: d.total_chunks !== undefined ? d.total_chunks : 0,
      entities: d.unique_entity_count || 0,
      size: `${(d.file_size / 1024).toFixed(1)} KB`,
      version: d.version,
      created_at: d.created_at,
      processed_at: d.processed_at,
      extracted_characters: d.extracted_text_length || 0,
      extracted_words: Math.round((d.extracted_text_length || 0) / 5),
      extraction_status: d.extraction_status,
      processing_error: d.processing_error,
      embedding_status: d.embedding_status,
      embedded_chunks: d.embedded_chunks,
      embedding_model: d.embedding_model,
      entity_extraction_status: d.entity_extraction_status,
      entity_mention_count: d.entity_mention_count,
      unique_entity_count: d.unique_entity_count,
      relationship_extraction_status: d.relationship_extraction_status,
      relationship_count: d.relationship_count,
    }));
    setDocuments(formatted);
  };

  const fetchLiveDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listDocuments({ limit: 100 });
      setIsBackendConnected(true);
      if (data.documents && data.documents.length > 0) {
        mapAndSetDocs(data.documents);
      } else {
        // If DB has no documents yet, retain default display documents
        setDocuments(RECENT_DOCUMENTS);
      }
    } catch {
      setIsBackendConnected(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLiveDocuments();
  }, [fetchLiveDocuments]);

  // Filter documents dynamically
  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchesSearch =
        doc.name.toLowerCase().includes(search.toLowerCase()) ||
        doc.owner.toLowerCase().includes(search.toLowerCase()) ||
        doc.department.toLowerCase().includes(search.toLowerCase());

      const matchesDept =
        departmentFilter === "All" || doc.department === departmentFilter;
      const matchesType = typeFilter === "All" || doc.type === typeFilter;
      const matchesStatus =
        statusFilter === "All" || doc.status === statusFilter;

      return matchesSearch && matchesDept && matchesType && matchesStatus;
    });
  }, [documents, search, departmentFilter, typeFilter, statusFilter]);

  const handleDelete = async (id: string) => {
    setDocuments((prev) => prev.filter((d) => d.id !== id));
    if (isBackendConnected) {
      try {
        await deleteDocument(id);
      } catch (err) {
        console.warn("Could not delete from backend:", err);
      }
    }
  };

  const handleUploadSuccess = (uploadedDoc: any) => {
    if (uploadedDoc && uploadedDoc.id) {
      const formatted: RecentDocumentItem = {
        id: uploadedDoc.id,
        name: uploadedDoc.filename,
        type: (uploadedDoc.file_type ? uploadedDoc.file_type.toUpperCase() : "PDF") as any,
        department: uploadedDoc.department || "Engineering",
        updated: "Just now",
        status: "Uploaded",
        owner: uploadedDoc.owner || "Alex Morgan",
        chunks: uploadedDoc.total_chunks !== undefined ? uploadedDoc.total_chunks : 0,
        entities: 0,
        size: `${((uploadedDoc.file_size || 1024) / 1024).toFixed(1)} KB`,
      };
      setDocuments((prev) => [formatted, ...prev]);
    } else {
      fetchLiveDocuments();
    }
  };

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-white">
              Documents
            </h2>
            {isBackendConnected ? (
              <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Database className="w-3 h-3" /> PostgreSQL Connected
              </span>
            ) : (
              <span className="px-2 py-0.5 text-[10px] font-semibold rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                Standalone UI Mode
              </span>
            )}
          </div>
          <p className="text-xs sm:text-sm text-slate-400 mt-1">
            Manage your enterprise knowledge sources, metadata, and document lifecycles.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={fetchLiveDocuments}
            variant="outline"
            size="md"
            title="Refresh documents list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
          </Button>

          <Button
            onClick={() => setIsUploadModalOpen(true)}
            variant="primary"
            size="md"
          >
            <Upload className="w-4 h-4 mr-2" />
            <span>Upload Document</span>
          </Button>
        </div>
      </div>

      {/* Search and Filters Bar */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="lg:col-span-2">
          <SearchInput
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onClear={() => setSearch("")}
            placeholder="Search by filename, owner, or department..."
          />
        </div>

        <div>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="w-full h-10 px-3 text-sm bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-brand-500 transition-colors"
          >
            <option value="All">All Departments</option>
            <option value="Engineering">Engineering</option>
            <option value="Security">Security</option>
            <option value="Product">Product</option>
            <option value="Legal">Legal</option>
            <option value="Finance">Finance</option>
          </select>
        </div>

        <div>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="w-full h-10 px-3 text-sm bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-brand-500 transition-colors"
          >
            <option value="All">All Formats</option>
            <option value="PDF">PDF</option>
            <option value="DOCX">DOCX</option>
            <option value="TXT">TXT</option>
            <option value="MD">Markdown</option>
            <option value="CSV">CSV</option>
          </select>
        </div>

        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="w-full h-10 px-3 text-sm bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-brand-500 transition-colors"
          >
            <option value="All">All Statuses</option>
            <option value="Processed">Processed</option>
            <option value="Processing">Processing</option>
            <option value="Uploaded">Uploaded</option>
            <option value="Failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Documents Table or Empty State */}
      {filteredDocs.length > 0 ? (
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-1 backdrop-blur-sm">
          <DocumentTable
            documents={filteredDocs}
            onDeleteDocument={handleDelete}
            onDocumentUpdated={fetchLiveDocuments}
          />
        </div>
      ) : (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 backdrop-blur-sm">
          <EmptyState
            title="No documents match your filters"
            description="Try changing your search terms or resetting the department, format, or status filters."
            actionLabel="Reset Filters"
            onAction={() => {
              setSearch("");
              setDepartmentFilter("All");
              setTypeFilter("All");
              setStatusFilter("All");
            }}
          />
        </div>
      )}

      {/* Upload Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadSuccess={handleUploadSuccess}
      />
    </div>
  );
}
