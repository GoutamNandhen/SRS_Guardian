"use client";

import React, { useEffect, useState, useRef } from "react";
import Link from "next/link";
import {
  FileText,
  Upload,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Play,
  Trash2,
  ExternalLink,
  Search,
  Filter,
  RefreshCw,
  FileCode,
  FileSpreadsheet,
  Layers,
  ArrowRight,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import { DocumentListItem } from "@/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Upload state
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);

  // Analysis state per document id
  const [analyzingDocId, setAnalyzingDocId] = useState<number | null>(null);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "analyzed" | "uploaded" | "extracted">("all");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Format file size nicely
  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Handle file upload
  const handleFileUpload = async (file: File) => {
    setUploadError(null);
    setUploadSuccess(null);
    setActionNotice(null);

    // Validate size (20MB)
    if (file.size > 20 * 1024 * 1024) {
      setUploadError("File exceeds the maximum 20MB limit.");
      return;
    }

    // Validate extension
    const validExtensions = [".txt", ".docx", ".pdf", ".md"];
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() || "");
    if (!validExtensions.includes(ext)) {
      setUploadError(`Unsupported file format '${ext}'. Please upload a PDF, DOCX, or TXT file.`);
      return;
    }

    try {
      setUploading(true);
      const newDoc = await api.uploadDocument(file);
      setUploadSuccess(`Successfully ingested "${newDoc.filename}".`);
      await fetchDocuments();
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload file");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  // Handle document analysis
  const handleAnalyze = async (docId: number, filename: string) => {
    try {
      setAnalyzingDocId(docId);
      setActionNotice(null);
      const res = await api.analyzeDocument(docId);
      setActionNotice({
        type: "success",
        message: `Analysis completed for "${filename}": ${res.requirements_count} requirements extracted & scored, ${res.issues_count} potential issues detected.`,
      });
      await fetchDocuments();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: `Analysis failed for "${filename}": ${err.message || "Unknown error"}`,
      });
    } finally {
      setAnalyzingDocId(null);
    }
  };

  // Handle document deletion
  const handleDelete = async (docId: number, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"? All associated requirements and review records will be removed.`)) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      setActionNotice({
        type: "success",
        message: `Document "${filename}" has been deleted.`,
      });
      await fetchDocuments();
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: `Failed to delete "${filename}": ${err.message}`,
      });
    }
  };

  // Filter documents
  const filteredDocs = documents.filter((doc) => {
    const matchesSearch =
      doc.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
      doc.file_type.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || doc.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getFormatBadge = (fileType: string) => {
    const t = fileType.toLowerCase();
    if (t === "pdf") {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-red-50 text-red-700 border border-red-200">
          PDF
        </span>
      );
    }
    if (t === "docx") {
      return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-blue-50 text-blue-700 border border-blue-200">
          DOCX
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[11px] font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
        TXT
      </span>
    );
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "analyzed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-600"></span>
            Analysed
          </span>
        );
      case "extracted":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-indigo-50 text-indigo-800 border border-indigo-200">
            <span className="w-1.5 h-1.5 rounded-full bg-indigo-600"></span>
            Extracted
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-rose-50 text-rose-800 border border-rose-200">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
            Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-blue-50 text-blue-800 border border-blue-200">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
            Uploaded
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-5 w-full max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-on-surface">
              Documents
            </h1>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/50">
              {documents.length} {documents.length === 1 ? "file" : "files"}
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Software Requirements Specification repository • ISO/IEC/IEEE 29148 decomposition engine
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {/* Search Box */}
          <div className="relative flex items-center w-56 h-8 px-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 focus-within:border-secondary transition-all">
            <Search className="w-3.5 h-3.5 text-outline mr-1.5 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search specifications..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent border-none outline-none text-xs text-on-surface placeholder:text-outline"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="text-xs text-outline hover:text-on-surface"
              >
                ×
              </button>
            )}
          </div>

          {/* Trigger browse */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-primary text-on-primary text-xs font-medium hover:bg-primary-container transition-colors shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload SRS</span>
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-start gap-2.5 ${
            actionNotice.type === "success"
              ? "bg-emerald-50 text-emerald-900 border-emerald-200"
              : "bg-rose-50 text-rose-900 border-rose-200"
          }`}
        >
          {actionNotice.type === "success" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
          ) : (
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="font-medium">{actionNotice.message}</p>
          </div>
          <button
            type="button"
            onClick={() => setActionNotice(null)}
            className="text-xs opacity-60 hover:opacity-100 font-bold ml-2"
          >
            ✕
          </button>
        </div>
      )}

      {/* Upload Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`p-4 rounded-xl border border-dashed transition-all ${
          isDragging
            ? "border-secondary bg-surface-container-high/60 shadow-md"
            : "border-outline-variant/80 bg-surface-container-lowest hover:border-secondary/70"
        }`}
      >
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-surface-container-low flex items-center justify-center flex-shrink-0 text-secondary border border-outline-variant/40">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-on-surface">
                  Drag and drop an SRS file, or browse your local system
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/40">
                  MAX 20MB
                </span>
              </div>
              <p className="text-[11px] text-outline mt-0.5">
                Supported formats: PDF, DOCX, TXT • Direct plain-text and structured parsing
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileUpload(e.target.files[0]);
                }
              }}
              className="hidden"
            />
            <button
              type="button"
              disabled={uploading}
              onClick={() => fileInputRef.current?.click()}
              className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-surface-container-low border border-outline-variant/60 hover:bg-surface-container text-on-surface text-xs font-medium transition-colors disabled:opacity-50"
            >
              <Upload className="w-3.5 h-3.5 text-outline" />
              <span>{uploading ? "Ingesting..." : "Browse files"}</span>
            </button>
          </div>
        </div>

        {uploadError && (
          <div className="mt-3 p-2 rounded bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {uploadSuccess && (
          <div className="mt-3 p-2 rounded bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{uploadSuccess}</span>
          </div>
        )}
      </div>

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setStatusFilter("all")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === "all"
                ? "bg-surface-container-high text-on-surface font-semibold shadow-xs"
                : "text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            All ({documents.length})
          </button>
          <button
            onClick={() => setStatusFilter("analyzed")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
              statusFilter === "analyzed"
                ? "bg-surface-container-high text-on-surface font-semibold shadow-xs"
                : "text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
            Analysed ({documents.filter((d) => d.status === "analyzed").length})
          </button>
          <button
            onClick={() => setStatusFilter("uploaded")}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
              statusFilter === "uploaded"
                ? "bg-surface-container-high text-on-surface font-semibold shadow-xs"
                : "text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500"></span>
            Uploaded ({documents.filter((d) => d.status === "uploaded").length})
          </button>
        </div>

        <button
          onClick={fetchDocuments}
          disabled={loading}
          className="inline-flex items-center gap-1 text-xs text-outline hover:text-on-surface transition-colors"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Table / List Area */}
      {loading ? (
        <LoadingState message="Loading document repository..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchDocuments} className="my-6" />
      ) : filteredDocs.length === 0 ? (
        <EmptyState
          title={searchQuery ? "No matching documents found" : "No specifications uploaded yet"}
          description={
            searchQuery
              ? `No specifications match your search query "${searchQuery}".`
              : "Upload an SRS document in PDF, DOCX, or plain text format to start automated requirement extraction and analysis."
          }
          actionLabel={searchQuery ? "Clear Search" : "Upload Document"}
          onAction={() => {
            if (searchQuery) {
              setSearchQuery("");
            } else {
              fileInputRef.current?.click();
            }
          }}
          icon={<FileText className="w-6 h-6 text-outline" />}
        />
      ) : (
        <div className="rounded-xl border border-outline-variant/60 bg-surface-container-lowest overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="h-9 border-b border-outline-variant/50 bg-surface-container-low/70 text-outline uppercase font-semibold text-[10px] tracking-wider select-none">
                  <th className="px-4 py-2">Document Name</th>
                  <th className="px-3 py-2">Format</th>
                  <th className="px-3 py-2">Size</th>
                  <th className="px-3 py-2">Pages</th>
                  <th className="px-3 py-2">Requirements</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Uploaded</th>
                  <th className="px-4 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/30 text-on-surface">
                {filteredDocs.map((doc) => {
                  const reqCount = doc.requirement_count ?? doc.requirements_count ?? 0;
                  const isAnalyzing = analyzingDocId === doc.id;

                  return (
                    <tr
                      key={doc.id}
                      className="hover:bg-surface-container-low/40 transition-colors group"
                    >
                      {/* Document Name */}
                      <td className="px-4 py-3 font-medium">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded bg-surface-container flex items-center justify-center flex-shrink-0 text-on-surface-variant">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <div className="flex flex-col">
                            <span className="font-semibold text-on-surface truncate max-w-xs md:max-w-sm">
                              {doc.filename}
                            </span>
                            <span className="text-[10px] text-outline font-mono">
                              ID: #{doc.id}
                            </span>
                          </div>
                        </div>
                      </td>

                      {/* Format */}
                      <td className="px-3 py-3">
                        {getFormatBadge(doc.file_type)}
                      </td>

                      {/* Size */}
                      <td className="px-3 py-3 font-mono text-[11px] text-on-surface-variant">
                        {formatFileSize(doc.file_size)}
                      </td>

                      {/* Pages */}
                      <td className="px-3 py-3 font-mono text-[11px] text-outline">
                        {doc.page_count} {doc.page_count === 1 ? "page" : "pages"}
                      </td>

                      {/* Requirements */}
                      <td className="px-3 py-3 font-mono font-medium">
                        {reqCount > 0 ? (
                          <span className="inline-flex items-center px-2 py-0.5 rounded bg-surface-container text-on-surface font-mono text-[11px]">
                            {reqCount} reqs
                          </span>
                        ) : (
                          <span className="text-outline text-[11px]">—</span>
                        )}
                      </td>

                      {/* Status */}
                      <td className="px-3 py-3">
                        {isAnalyzing ? (
                          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-amber-50 text-amber-800 border border-amber-200 animate-pulse">
                            <RefreshCw className="w-3 h-3 animate-spin" />
                            Analyzing...
                          </span>
                        ) : (
                          getStatusBadge(doc.status)
                        )}
                      </td>

                      {/* Uploaded */}
                      <td className="px-3 py-3 text-outline text-[11px]">
                        {new Date(doc.uploaded_at).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1.5 justify-end">
                          {/* Analyze Button */}
                          <button
                            type="button"
                            disabled={isAnalyzing}
                            onClick={() => handleAnalyze(doc.id, doc.filename)}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded bg-surface-container hover:bg-secondary hover:text-on-secondary text-on-surface text-[11px] font-medium transition-colors disabled:opacity-50"
                            title="Run automated ISO 29148 checks and requirement scoring"
                          >
                            <Play className="w-3 h-3" />
                            <span>{doc.status === "analyzed" ? "Re-Analyze" : "Analyze"}</span>
                          </button>

                          {/* View Requirements */}
                          <Link
                            href={`/requirements?doc=${doc.id}`}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface text-[11px] font-medium transition-colors"
                            title="Open in Requirement Viewer"
                          >
                            <Layers className="w-3 h-3 text-outline" />
                            <span>View Reqs</span>
                          </Link>

                          {/* View Reports */}
                          <Link
                            href={`/reports?doc=${doc.id}`}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded bg-surface-container hover:bg-surface-container-high text-on-surface text-[11px] font-medium transition-colors"
                            title="Export and view reports"
                          >
                            <FileSpreadsheet className="w-3 h-3 text-outline" />
                            <span>Reports</span>
                          </Link>

                          {/* Delete Document */}
                          <button
                            type="button"
                            onClick={() => handleDelete(doc.id, doc.filename)}
                            className="p-1.5 rounded text-outline hover:text-rose-600 hover:bg-rose-50 transition-colors"
                            title="Delete document"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
