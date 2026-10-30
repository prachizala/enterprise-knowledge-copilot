"use client";

import React, { useState, useRef } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { UploadCloud, FileText, CheckCircle2, AlertCircle, X, Loader2 } from "lucide-react";
import { uploadDocument, DocumentResponse } from "@/lib/api";

export interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess?: (doc: DocumentResponse) => void;
}

const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB
const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt", ".csv"];

export function DocumentUploadModal({
  isOpen,
  onClose,
  onUploadSuccess,
}: DocumentUploadModalProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [department, setDepartment] = useState("Engineering");
  const [owner, setOwner] = useState("Alex Morgan");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStep, setUploadStep] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const validateAndSetFile = (file: File) => {
    setError(null);
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      setError(`Unsupported file type '${ext}'. Only PDF, DOCX, TXT, and CSV are allowed.`);
      setSelectedFile(null);
      return;
    }

    if (file.size > MAX_FILE_SIZE_BYTES) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds maximum allowed 50 MB limit.`);
      setSelectedFile(null);
      return;
    }

    if (file.size === 0) {
      setError("The selected file is empty (0 bytes).");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleTriggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  const handleUploadSubmit = async () => {
    if (!selectedFile) {
      setError("Please select a document to upload.");
      return;
    }

    setIsUploading(true);
    setUploadStep("Uploading file to server...");
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("department", department);
      formData.append("owner", owner);
      formData.append(
        "description",
        `Enterprise document uploaded for ${department} department`
      );

      setUploadStep("Extracting text and structure...");
      const doc = await uploadDocument(formData);

      if (doc.status === "failed") {
        setError(`Extraction notice: ${doc.processing_error || "Could not extract text from document."}`);
      } else {
        setIsSuccess(true);
      }

      if (onUploadSuccess) {
        onUploadSuccess(doc);
      }

      setTimeout(() => {
        setIsSuccess(false);
        setSelectedFile(null);
        setUploadStep(null);
        onClose();
      }, 1400);
    } catch (err: any) {
      logger_or_warn: console.warn("Backend upload error, checking fallback:", err);
      setError(err.message || "Failed to upload document. Please ensure the backend is running.");
    } finally {
      setIsUploading(false);
      setUploadStep(null);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Upload Enterprise Document"
      description="Upload structured and unstructured files (PDF, DOCX, TXT, CSV) for automated text extraction and metadata indexing."
    >
      <div className="space-y-4">
        {/* Hidden input for real files */}
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.csv"
          onChange={handleFileChange}
          className="hidden"
          disabled={isUploading}
        />

        {error && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-300 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <span className="leading-relaxed">{error}</span>
          </div>
        )}

        {/* Dropzone */}
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          onClick={handleTriggerFileSelect}
          className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center cursor-pointer transition-colors bg-slate-950/60 group ${
            isUploading
              ? "border-slate-800 opacity-60 cursor-not-allowed"
              : "border-slate-700 hover:border-indigo-500"
          }`}
        >
          <div className="mx-auto w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform mb-3">
            {isUploading ? (
              <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
            ) : (
              <UploadCloud className="w-6 h-6" />
            )}
          </div>
          <p className="text-sm font-semibold text-white">
            {isUploading ? "Processing document..." : "Drag and drop your file here"}
          </p>
          <p className="text-xs text-slate-400 mt-1">
            or <span className="text-indigo-400 underline font-medium">Choose File</span>
          </p>
          <div className="flex items-center justify-center gap-4 text-[11px] text-slate-500 mt-3 pt-3 border-t border-slate-800/60">
            <span>Supported: <strong>PDF, DOCX, TXT, CSV</strong></span>
            <span>•</span>
            <span>Maximum size: <strong>50 MB</strong></span>
          </div>
        </div>

        {/* Selected file preview */}
        {selectedFile && (
          <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <FileText className="w-4 h-4 text-indigo-400" />
              <div>
                <p className="text-xs font-medium text-white truncate max-w-[280px]">
                  {selectedFile.name}
                </p>
                <p className="text-[10px] text-slate-400">
                  {(selectedFile.size / 1024).toFixed(1)} KB • {selectedFile.name.split(".").pop()?.toUpperCase()}
                </p>
              </div>
            </div>
            {!isUploading && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedFile(null);
                  setError(null);
                }}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        {/* Processing Indicator */}
        {isUploading && uploadStep && (
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-indigo-300 flex items-center gap-2 animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400 shrink-0" />
            <span>{uploadStep}</span>
          </div>
        )}

        {/* Department and Owner Form */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Department
            </label>
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              disabled={isUploading}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
            >
              <option value="Engineering">Engineering</option>
              <option value="Security">Security &amp; Compliance</option>
              <option value="Human Resources">Human Resources</option>
              <option value="Finance">Finance</option>
              <option value="Legal">Legal &amp; Contracts</option>
            </select>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">
              Owner / Author
            </label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              disabled={isUploading}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 disabled:opacity-50"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={isUploading}>
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleUploadSubmit}
            disabled={!selectedFile || isUploading}
            isLoading={isUploading}
          >
            {isSuccess ? (
              <span className="flex items-center gap-1.5 text-emerald-300">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Processed
              </span>
            ) : (
              "Upload & Process"
            )}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
