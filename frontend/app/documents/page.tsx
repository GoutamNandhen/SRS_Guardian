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
  RefreshCw,
  FileSpreadsheet,
  Layers,
  ArrowRight,
  FileCheck,
  RotateCcw,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import { DocumentListItem, DocumentAnalysisResponse } from "@/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // File selection state before analysis
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  // Compact summary result from real analysis (Phase 18.2)
  const [analysisResult, setAnalysisResult] = useState<DocumentAnalysisResponse | null>(null);

  // Per-row analysis state
  const [analyzingDocId, setAnalyzingDocId] = useState<number | null>(null);
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "analyzed" | "uploaded">("all");

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

  const formatFileSize = (bytes: number) => {
    if (!bytes || bytes === 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Stage 1: File selection validation
  const handleSelectFile = (file: File) => {
    setAnalysisError(null);
    setActionNotice(null);

    // Validate size (20MB)
    if (file.size > 20 * 1024 * 1024) {
      setAnalysisError("File exceeds the maximum 20MB limit.");
      return;
    }

    // Validate extension
    const validExtensions = [".txt", ".docx", ".pdf", ".md"];
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() || "");
    if (!validExtensions.includes(ext)) {
      setAnalysisError(`Unsupported file format '${ext}'. Please upload a PDF, DOCX, or TXT specification.`);
      return;
    }

    setSelectedFile(file);
    setAnalysisResult(null);
  };

  // Stage 2: Ingest & Analyze Requirements (End-to-End Pipeline)
  const handleAnalyzeSelectedFile = async () => {
    if (!selectedFile) return;

    try {
      setAnalyzing(true);
      setAnalysisError(null);

      // 1. Ingest document
      const doc = await api.uploadDocument(selectedFile);

      // 2. Run real extraction & analysis pipeline
      const result = await api.analyzeDocument(doc.id);

      // Ensure filename is attached
      if (!result.filename) {
        result.filename = doc.filename;
      }

      setAnalysisResult(result);
      setSelectedFile(null);
      await fetchDocuments();
    } catch (err: any) {
      setAnalysisError(err.message || "Analysis failed during document processing");
      // Refresh documents in case ingestion succeeded but analysis failed
      await fetchDocuments().catch(() => {});
    } finally {
      setAnalyzing(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // Drag and drop handlers
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
      handleSelectFile(e.dataTransfer.files[0]);
    }
  };

  // Analyze an existing document from the table
  const handleAnalyzeExisting = async (docId: number, filename: string) => {
    try {
      setAnalyzingDocId(docId);
      setActionNotice(null);
      const res = await api.analyzeDocument(docId);
      if (!res.filename) res.filename = filename;
      setAnalysisResult(res);
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
    if (
      !confirm(
        `Are you sure you want to delete "${filename}"? All associated requirements and review records will be removed.`
      )
    ) {
      return;
    }
    try {
      await api.deleteDocument(docId);
      if (analysisResult?.document_id === docId) {
        setAnalysisResult(null);
      }
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
    <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto pb-12">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-on-surface">Documents</h1>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/50">
              {documents.length} {documents.length === 1 ? "file" : "files"}
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Software Requirements Specification repository • Automated ISO/IEC/IEEE 29148 analysis pipeline
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

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-xs"
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Upload SRS</span>
          </button>
        </div>
      </div>

      {/* Hidden File Input */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={(e) => {
          if (e.target.files && e.target.files.length > 0) {
            handleSelectFile(e.target.files[0]);
          }
        }}
        className="hidden"
      />

      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3 rounded-xl border text-xs flex items-start gap-2.5 ${
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

      {/* PHASE 18.2: Compact Analysis Complete Card */}
      {analysisResult && (
        <div className="rounded-2xl border-2 border-emerald-500/50 bg-surface shadow-md overflow-hidden animate-in fade-in duration-300">
          <div className="p-5 border-b border-outline-variant/30 bg-emerald-50/60 dark:bg-emerald-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center flex-shrink-0 shadow-xs">
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-base font-bold text-on-surface">Analysis Complete ✓</h2>
                  <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-300 font-semibold">
                    Real Pipeline Verified
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant mt-0.5">
                  Document: <strong className="text-on-surface">{analysisResult.filename || "Uploaded Document"}</strong>
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => setAnalysisResult(null)}
              className="text-xs text-outline hover:text-on-surface self-end sm:self-center font-medium"
            >
              Dismiss
            </button>
          </div>

          <div className="p-6">
            {/* Metric Counters Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
              <div className="p-3.5 rounded-xl border border-outline-variant/40 bg-surface-container-low/60 flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-outline">
                  Requirements
                </span>
                <span className="text-2xl font-black text-on-surface mt-1">
                  {analysisResult.requirements_count}
                </span>
                <span className="text-[10px] text-outline mt-0.5">analyzed</span>
              </div>

              <div className="p-3.5 rounded-xl border border-amber-300/60 bg-amber-50/40 dark:bg-amber-950/20 flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 dark:text-amber-400">
                  Needs Attention
                </span>
                <span className="text-2xl font-black text-amber-800 dark:text-amber-300 mt-1">
                  {analysisResult.needs_attention_count ??
                    (analysisResult.quality_summary?.worst_requirements?.length || 0)}
                </span>
                <span className="text-[10px] text-amber-600/80 mt-0.5">items flagged</span>
              </div>

              <div className="p-3.5 rounded-xl border border-rose-300/60 bg-rose-50/40 dark:bg-rose-950/20 flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-rose-700 dark:text-rose-400">
                  Critical
                </span>
                <span className="text-2xl font-black text-rose-800 dark:text-rose-300 mt-1">
                  {analysisResult.critical_count ?? 0}
                </span>
                <span className="text-[10px] text-rose-600/80 mt-0.5">high severity</span>
              </div>

              <div className="p-3.5 rounded-xl border border-amber-200/60 bg-surface-container-low/60 flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-outline">
                  Warnings
                </span>
                <span className="text-2xl font-black text-on-surface mt-1">
                  {analysisResult.warning_count ??
                    Math.max(0, analysisResult.issues_count - (analysisResult.critical_count || 0))}
                </span>
                <span className="text-[10px] text-outline mt-0.5">potential issues</span>
              </div>

              <div className="p-3.5 rounded-xl border border-emerald-300/60 bg-emerald-50/40 dark:bg-emerald-950/20 flex flex-col">
                <span className="text-[10px] font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-400">
                  No Issues
                </span>
                <span className="text-2xl font-black text-emerald-800 dark:text-emerald-300 mt-1">
                  {analysisResult.no_issues_count ??
                    Math.max(
                      0,
                      analysisResult.requirements_count - (analysisResult.needs_attention_count || 0)
                    )}
                </span>
                <span className="text-[10px] text-emerald-600/80 mt-0.5">acceptable</span>
              </div>
            </div>

            {/* Action Buttons as specified in Phase 18.2 Prompt Pack */}
            <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-outline-variant/30">
              {/* 1. Review Requirements */}
              <Link
                href={`/reports/review?doc=${analysisResult.document_id}`}
                className="inline-flex items-center gap-2 h-9 px-4 rounded-xl bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all shadow-xs"
              >
                <FileCheck className="w-4 h-4" />
                <span>Review Requirements</span>
                <ArrowRight className="w-3.5 h-3.5 opacity-70" />
              </Link>

              {/* 2. View Annotated SRS */}
              <a
                href={api.getAnnotatedPdfUrl(analysisResult.document_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 h-9 px-4 rounded-xl bg-surface-container border border-outline-variant/60 text-on-surface text-xs font-semibold hover:bg-surface-container-high transition-colors"
              >
                <ExternalLink className="w-3.5 h-3.5 text-outline" />
                <span>View Annotated SRS</span>
              </a>

              {/* 3. Generate Report */}
              <Link
                href={`/reports?doc=${analysisResult.document_id}`}
                className="inline-flex items-center gap-2 h-9 px-4 rounded-xl bg-surface-container border border-outline-variant/60 text-on-surface text-xs font-semibold hover:bg-surface-container-high transition-colors"
              >
                <FileSpreadsheet className="w-3.5 h-3.5 text-outline" />
                <span>Generate Report</span>
              </Link>

              {/* Reset to analyze another file */}
              <button
                type="button"
                onClick={() => setAnalysisResult(null)}
                className="inline-flex items-center gap-1.5 h-9 px-3 rounded-xl text-outline hover:text-on-surface text-xs font-medium transition-colors ml-auto"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Analyze Another SRS</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PHASE 18.2: File Selection & Ready State Dropzone */}
      {!analysisResult && (
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          className={`p-6 rounded-2xl border-2 border-dashed transition-all ${
            isDragging
              ? "border-primary bg-primary/5 shadow-md"
              : selectedFile
              ? "border-emerald-500/70 bg-emerald-50/20 shadow-xs"
              : "border-outline-variant/80 bg-surface hover:border-primary/50"
          }`}
        >
          {!selectedFile ? (
            /* Empty selection state: choose or drag file */
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-surface-container-low flex items-center justify-center flex-shrink-0 text-primary border border-outline-variant/40 shadow-xs">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold text-on-surface">Upload SRS Document</span>
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/40">
                      MAX 20MB
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-0.5">
                    Upload your Software Requirements Specification to analyze its requirements.
                  </p>
                  <p className="text-[11px] text-outline mt-1 font-mono">
                    Supported: PDF • DOCX • TXT
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="w-full sm:w-auto inline-flex items-center justify-center gap-2 h-9 px-4 rounded-xl bg-surface-container border border-outline-variant/60 hover:bg-surface-container-high text-on-surface text-xs font-semibold transition-colors"
                >
                  <Upload className="w-3.5 h-3.5 text-outline" />
                  <span>Choose File</span>
                </button>
              </div>
            </div>
          ) : (
            /* Selected state: filename -> ✓ File ready -> [ Analyze Requirements ] */
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-3.5">
                <div className="w-11 h-11 rounded-xl bg-emerald-500/10 text-emerald-600 flex items-center justify-center flex-shrink-0 border border-emerald-300 shadow-xs">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-bold text-on-surface truncate max-w-sm sm:max-w-md">
                      {selectedFile.name}
                    </span>
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300 border border-emerald-300">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      ✓ File ready
                    </span>
                  </div>
                  <p className="text-xs text-outline mt-0.5 font-mono">
                    {formatFileSize(selectedFile.size)} • {selectedFile.name.split(".").pop()?.toUpperCase()} format
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto">
                <button
                  type="button"
                  disabled={analyzing}
                  onClick={() => setSelectedFile(null)}
                  className="px-3 h-9 rounded-xl border border-outline-variant/50 text-xs text-outline hover:text-on-surface transition-colors disabled:opacity-50"
                >
                  Change File
                </button>

                <button
                  type="button"
                  disabled={analyzing}
                  onClick={handleAnalyzeSelectedFile}
                  className="flex-1 sm:flex-initial inline-flex items-center justify-center gap-2 h-9 px-5 rounded-xl bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-all shadow-xs disabled:opacity-50"
                >
                  {analyzing ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Analyzing Requirements...</span>
                    </>
                  ) : (
                    <>
                      <Play className="w-3.5 h-3.5 fill-current" />
                      <span>Analyze Requirements</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {analysisError && (
            <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2.5">
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
              <span>{analysisError}</span>
            </div>
          )}
        </div>
      )}

      {/* Filter Chips Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-2">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setStatusFilter("all")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              statusFilter === "all"
                ? "bg-surface-container-high text-on-surface font-semibold shadow-xs"
                : "text-on-surface-variant hover:bg-surface-container"
            }`}
          >
            All Documents ({documents.length})
          </button>
          <button
            onClick={() => setStatusFilter("analyzed")}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
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
            className={`px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-colors ${
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
          className="inline-flex items-center gap-1.5 text-xs text-outline hover:text-on-surface transition-colors font-medium"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh List</span>
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
        <div className="rounded-2xl border border-outline-variant/60 bg-surface shadow-xs overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="h-10 border-b border-outline-variant/50 bg-surface-container-low/70 text-outline uppercase font-semibold text-[10px] tracking-wider select-none">
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
                          <div className="w-7 h-7 rounded-lg bg-surface-container flex items-center justify-center flex-shrink-0 text-on-surface-variant">
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
                          {/* Analyze / Re-Analyze Button */}
                          <button
                            type="button"
                            disabled={isAnalyzing}
                            onClick={() => handleAnalyzeExisting(doc.id, doc.filename)}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg bg-surface-container hover:bg-secondary hover:text-secondary-foreground text-on-surface text-[11px] font-medium transition-colors disabled:opacity-50"
                            title="Run automated ISO 29148 checks and requirement scoring"
                          >
                            <Play className="w-3 h-3" />
                            <span>{doc.status === "analyzed" ? "Re-Analyze" : "Analyze"}</span>
                          </button>

                          {/* Review Requirements (Phase 18.1 Executive Review) */}
                          <Link
                            href={`/reports/review?doc=${doc.id}`}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg bg-primary/10 hover:bg-primary/20 text-primary text-[11px] font-semibold transition-colors"
                            title="Open in Executive Review"
                          >
                            <FileCheck className="w-3 h-3" />
                            <span>Review</span>
                          </Link>

                          {/* View Requirements */}
                          <Link
                            href={`/requirements?doc=${doc.id}`}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-[11px] font-medium transition-colors"
                            title="Open in Requirement Viewer"
                          >
                            <Layers className="w-3 h-3 text-outline" />
                            <span>Reqs</span>
                          </Link>

                          {/* View Reports */}
                          <Link
                            href={`/reports?doc=${doc.id}`}
                            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg bg-surface-container hover:bg-surface-container-high text-on-surface text-[11px] font-medium transition-colors"
                            title="Export and view reports"
                          >
                            <FileSpreadsheet className="w-3 h-3 text-outline" />
                            <span>Reports</span>
                          </Link>

                          {/* Delete Document */}
                          <button
                            type="button"
                            onClick={() => handleDelete(doc.id, doc.filename)}
                            className="p-1.5 rounded-lg text-outline hover:text-rose-600 hover:bg-rose-50 transition-colors"
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
