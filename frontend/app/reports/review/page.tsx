"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  FileCheck,
  Download,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  ChevronRight,
  Search,
  Sparkles,
  ArrowLeft,
  ExternalLink,
  Shield,
  Layers,
  HelpCircle,
  FileCode,
  Tag,
  Eye,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  DocumentReviewReport,
  RequirementReviewItem,
  AnnotatedFinding,
} from "@/types";

function DetailedReviewContent() {
  const searchParams = useSearchParams();
  const initialDocParam = searchParams.get("doc");

  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(
    initialDocParam ? parseInt(initialDocParam, 10) : null
  );

  const [report, setReport] = useState<DocumentReviewReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Navigation & Selection state
  const [selectedReqId, setSelectedReqId] = useState<number | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [moduleFilter, setModuleFilter] = useState<string>("all");
  const [confidenceFilter, setConfidenceFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"requirement" | "full_doc">("requirement");

  // 1. Load documents list
  useEffect(() => {
    async function loadDocs() {
      try {
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length > 0 && !selectedDocId) {
          const analyzed = docs.find((d) => d.status === "analyzed");
          setSelectedDocId(analyzed ? analyzed.id : docs[0].id);
        }
      } catch (err: any) {
        console.error("Failed to load documents list", err);
      }
    }
    loadDocs();
  }, [selectedDocId]);

  // 2. Fetch Review Report data when selectedDocId changes
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadReviewReport() {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getReviewReport(selectedDocId!);
        setReport(data);
        if (data.requirements && data.requirements.length > 0) {
          setSelectedReqId(data.requirements[0].requirement_id);
          if (data.requirements[0].findings && data.requirements[0].findings.length > 0) {
            setSelectedFindingId(data.requirements[0].findings[0].finding_id);
          } else {
            setSelectedFindingId(null);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load review report data.");
      } finally {
        setLoading(false);
      }
    }

    loadReviewReport();
  }, [selectedDocId]);

  // Filtered requirements list
  const filteredRequirements = useMemo(() => {
    if (!report) return [];
    return report.requirements.filter((req) => {
      // Search text match
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        req.req_key.toLowerCase().includes(q) ||
        req.text.toLowerCase().includes(q);

      // Module filter match
      const matchesModule =
        moduleFilter === "all" ||
        req.findings.some((f) => f.module.toLowerCase() === moduleFilter.toLowerCase());

      // Confidence filter match
      const matchesConfidence =
        confidenceFilter === "all" ||
        req.findings.some(
          (f) => f.confidence_band.toLowerCase() === confidenceFilter.toLowerCase()
        );

      return matchesSearch && matchesModule && matchesConfidence;
    });
  }, [report, searchQuery, moduleFilter, confidenceFilter]);

  // Selected requirement object
  const selectedReq = useMemo(() => {
    if (!report || !selectedReqId) return null;
    return report.requirements.find((r) => r.requirement_id === selectedReqId) || null;
  }, [report, selectedReqId]);

  // Selected finding object
  const selectedFinding = useMemo(() => {
    if (!report || !selectedFindingId) return null;
    return report.all_findings.find((f) => f.finding_id === selectedFindingId) || null;
  }, [report, selectedFindingId]);

  // Handler for clicking a requirement in the left pane
  const handleSelectReq = (req: RequirementReviewItem) => {
    setSelectedReqId(req.requirement_id);
    if (req.findings && req.findings.length > 0) {
      setSelectedFindingId(req.findings[0].finding_id);
    } else {
      setSelectedFindingId(null);
    }
  };

  // Helper to render requirement text with highlighted finding spans
  const renderHighlightedText = (req: RequirementReviewItem) => {
    const text = req.text;
    const findingsWithSpans = req.findings.filter((f) => f.has_sub_spans && f.spans.length > 0);

    if (findingsWithSpans.length === 0) {
      return (
        <p className="text-sm text-on-surface leading-relaxed whitespace-pre-wrap font-sans">
          {text}
        </p>
      );
    }

    // Collect all highlight slices
    type Slice = { start: number; end: number; finding: AnnotatedFinding };
    const slices: Slice[] = [];

    findingsWithSpans.forEach((f) => {
      f.spans.forEach((span) => {
        if (span.start >= 0 && span.end <= text.length && span.start < span.end) {
          slices.push({ start: span.start, end: span.end, finding: f });
        }
      });
    });

    // Sort slices by start position
    slices.sort((a, b) => a.start - b.start);

    // Build non-overlapping render fragments
    const fragments: React.ReactNode[] = [];
    let currentIndex = 0;

    slices.forEach((slice, idx) => {
      if (slice.start > currentIndex) {
        fragments.push(
          <span key={`plain-${currentIndex}`}>
            {text.slice(currentIndex, slice.start)}
          </span>
        );
      }

      const isSelected = selectedFindingId === slice.finding.finding_id;
      const sev = slice.finding.severity;
      const confBand = slice.finding.confidence_band;

      let hlClass = "bg-amber-100 text-amber-950 border-b-2 border-amber-500 hover:bg-amber-200";
      if (sev === "critical") {
        hlClass = "bg-rose-100 text-rose-950 border-b-2 border-rose-500 hover:bg-rose-200";
      } else if (sev === "info") {
        hlClass = "bg-sky-100 text-sky-950 border-b-2 border-sky-500 hover:bg-sky-200";
      }

      if (isSelected) {
        hlClass += " ring-2 ring-primary ring-offset-1 font-semibold";
      }

      fragments.push(
        <mark
          key={`span-${idx}`}
          onClick={(e) => {
            e.stopPropagation();
            setSelectedFindingId(slice.finding.finding_id);
          }}
          className={`cursor-pointer px-1 py-0.5 rounded transition-all duration-150 inline-flex items-center gap-1 ${hlClass}`}
          title={`Click to inspect: ${slice.finding.type} (${confBand.toUpperCase()} confidence)`}
        >
          <span>{text.slice(slice.start, slice.end)}</span>
          <span className="text-[9px] font-mono px-1 rounded bg-black/10 text-current uppercase leading-none py-0.5">
            {confBand}
          </span>
        </mark>
      );

      currentIndex = Math.max(currentIndex, slice.end);
    });

    if (currentIndex < text.length) {
      fragments.push(
        <span key={`tail-${currentIndex}`}>
          {text.slice(currentIndex)}
        </span>
      );
    }

    return (
      <div className="text-sm text-on-surface leading-relaxed whitespace-pre-wrap font-sans">
        {fragments}
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-surface-container-lowest flex flex-col">
      {/* Top Header */}
      <header className="bg-surface border-b border-outline-variant/40 px-6 py-3 flex items-center justify-between sticky top-0 z-30">
        <div className="flex items-center gap-4">
          <Link
            href="/reports"
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
            title="Back to Reports"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base font-bold text-on-surface tracking-tight">
                Explainable Review Report
              </h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-medium border border-primary/20">
                Phase 18 Detailed Audit
              </span>
            </div>
            <div className="flex items-center gap-3 text-xs text-on-surface-variant mt-0.5">
              <span>Document: <strong>{report?.filename || "Loading..."}</strong></span>
              <span>•</span>
              <span>Status: <strong className="uppercase text-emerald-600 font-semibold">{report?.status || "analyzed"}</strong></span>
              <span>•</span>
              <span>Requirements: <strong>{report?.total_requirements || 0}</strong></span>
              <span>•</span>
              <span>Findings: <strong>{report?.total_findings || 0}</strong></span>
            </div>
          </div>
        </div>

        {/* Header Document Switcher & Export Buttons */}
        <div className="flex items-center gap-2.5">
          {documents.length > 1 && (
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
              className="text-xs bg-surface-container-low border border-outline-variant/60 rounded-lg px-2.5 py-1.5 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.filename} (#{d.id})
                </option>
              ))}
            </select>
          )}

          {selectedDocId && (
            <div className="flex items-center gap-1.5">
              <a
                href={api.getAnnotatedPdfUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/60 text-xs font-medium text-on-surface hover:bg-surface-container transition-colors"
                title="Download source PDF with visual highlight annotations and audit legend"
              >
                <Download className="w-3.5 h-3.5 text-secondary" />
                Annotated PDF
              </a>

              <a
                href={api.getComprehensivePdfUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-surface-container-high border border-outline-variant/60 text-xs font-medium text-on-surface hover:bg-surface-container transition-colors"
                title="Download 19-section formal PDF audit report"
              >
                <FileText className="w-3.5 h-3.5 text-primary" />
                Audit PDF
              </a>

              <a
                href={api.getComprehensiveDocxUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-sm"
                title="Download editable 19-section Word DOCX audit report"
              >
                <FileCheck className="w-3.5 h-3.5" />
                DOCX Report
              </a>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center p-12">
          <LoadingState message="Compiling explainable review annotations and finding spans..." />
        </div>
      ) : error ? (
        <div className="flex-1 p-8 max-w-xl mx-auto">
          <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
        </div>
      ) : !report ? (
        <div className="flex-1 p-8">
          <EmptyState
            title="No Document Selected"
            description="Select an analyzed document to review exact finding highlights and explanations."
          />
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-12 overflow-hidden h-[calc(100vh-61px)]">
          {/* LEFT PANE: Navigation & Filters (3 Cols) */}
          <div className="col-span-3 border-r border-outline-variant/40 bg-surface-container-low flex flex-col h-full overflow-hidden">
            {/* Search & Filter Header */}
            <div className="p-3 border-b border-outline-variant/40 space-y-2 bg-surface">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-outline absolute left-2.5 top-2.5" />
                <input
                  type="text"
                  placeholder="Search requirement key or text..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-xs text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="grid grid-cols-2 gap-1.5">
                <div>
                  <label className="text-[10px] font-medium text-outline uppercase tracking-wider block mb-0.5">
                    Category
                  </label>
                  <select
                    value={moduleFilter}
                    onChange={(e) => setModuleFilter(e.target.value)}
                    className="w-full text-xs bg-surface-container-lowest border border-outline-variant/60 rounded px-2 py-1 text-on-surface focus:outline-none"
                  >
                    <option value="all">All Modules</option>
                    <option value="ambiguity">Ambiguity</option>
                    <option value="duplicates">Duplicates</option>
                    <option value="contradiction">Contradiction</option>
                    <option value="standards">Standards</option>
                  </select>
                </div>

                <div>
                  <label className="text-[10px] font-medium text-outline uppercase tracking-wider block mb-0.5">
                    Confidence
                  </label>
                  <select
                    value={confidenceFilter}
                    onChange={(e) => setConfidenceFilter(e.target.value)}
                    className="w-full text-xs bg-surface-container-lowest border border-outline-variant/60 rounded px-2 py-1 text-on-surface focus:outline-none"
                  >
                    <option value="all">All Confidence</option>
                    <option value="high">High (&ge; 80%)</option>
                    <option value="medium">Medium (60-79%)</option>
                    <option value="low">Low (&lt; 60%)</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Requirements List */}
            <div className="flex-1 overflow-y-auto divide-y divide-outline-variant/20 p-2 space-y-1">
              {filteredRequirements.length === 0 ? (
                <div className="p-4 text-center text-xs text-on-surface-variant">
                  No requirements match the current filters.
                </div>
              ) : (
                filteredRequirements.map((req) => {
                  const isSelected = selectedReqId === req.requirement_id;
                  const hasCritical = req.findings.some((f) => f.severity === "critical");
                  const hasWarning = req.findings.some((f) => f.severity === "warning");

                  return (
                    <div
                      key={req.requirement_id}
                      onClick={() => handleSelectReq(req)}
                      className={`p-2.5 rounded-lg cursor-pointer transition-all ${
                        isSelected
                          ? "bg-surface-container-high border-l-4 border-l-primary shadow-sm"
                          : "hover:bg-surface-container bg-surface border border-transparent"
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-xs font-bold text-on-surface">
                          {req.req_key}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                              req.quality_score >= 80
                                ? "bg-emerald-100 text-emerald-800"
                                : req.quality_score >= 60
                                ? "bg-amber-100 text-amber-800"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {Math.round(req.quality_score)}
                          </span>

                          {req.findings.length > 0 && (
                            <span
                              className={`w-2 h-2 rounded-full ${
                                hasCritical
                                  ? "bg-rose-500"
                                  : hasWarning
                                  ? "bg-amber-500"
                                  : "bg-sky-500"
                              }`}
                              title={`${req.findings.length} findings`}
                            />
                          )}
                        </div>
                      </div>

                      <p className="text-[11px] text-on-surface-variant line-clamp-2 leading-snug">
                        {req.text}
                      </p>

                      <div className="flex items-center gap-1.5 mt-2">
                        {req.findings.map((f) => (
                          <span
                            key={f.finding_id}
                            className={`text-[9px] font-mono px-1.5 py-0.5 rounded ${
                              f.severity === "critical"
                                ? "bg-rose-100 text-rose-800"
                                : f.severity === "warning"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-sky-100 text-sky-800"
                            }`}
                          >
                            {f.type.replace("CHECK_", "").slice(0, 10)}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* CENTER PANE: Source Viewer & Highlights (5 Cols) */}
          <div className="col-span-5 bg-surface flex flex-col h-full border-r border-outline-variant/40 overflow-hidden">
            {/* View Mode Switcher Header */}
            <div className="p-3 border-b border-outline-variant/40 flex items-center justify-between bg-surface-container-lowest">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-on-surface">
                  Source Inspection
                </span>
                <span className="text-[10px] text-on-surface-variant">
                  (Interactive Span Highlights)
                </span>
              </div>

              <div className="flex items-center bg-surface-container rounded-lg p-0.5 border border-outline-variant/60">
                <button
                  onClick={() => setViewMode("requirement")}
                  className={`px-2 py-1 text-[11px] font-medium rounded ${
                    viewMode === "requirement"
                      ? "bg-surface text-on-surface shadow-xs font-semibold"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  Active Requirement
                </button>
                <button
                  onClick={() => setViewMode("full_doc")}
                  className={`px-2 py-1 text-[11px] font-medium rounded ${
                    viewMode === "full_doc"
                      ? "bg-surface text-on-surface shadow-xs font-semibold"
                      : "text-on-surface-variant hover:text-on-surface"
                  }`}
                >
                  Full Document
                </button>
              </div>
            </div>

            {/* Document Content View */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {viewMode === "requirement" ? (
                selectedReq ? (
                  <div className="space-y-4">
                    {/* Requirement Card Header */}
                    <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/40 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm font-bold text-on-surface">
                            {selectedReq.req_key}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded bg-surface border border-outline-variant/60 text-on-surface-variant">
                            {selectedReq.classification_label || "Unclassified"}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                            EARS: {selectedReq.ears_pattern || "Non-conforming"}
                          </span>
                        </div>

                        <div className="text-right">
                          <span className="text-xs text-outline block">Quality Score</span>
                          <span className="text-base font-bold text-on-surface">
                            {Math.round(selectedReq.quality_score)} / 100
                          </span>
                        </div>
                      </div>

                      {/* Requirement Highlighted Text */}
                      <div className="p-4 rounded-lg bg-surface border border-outline-variant/60 shadow-xs">
                        {renderHighlightedText(selectedReq)}
                      </div>

                      {/* Finding indicator pill list */}
                      {selectedReq.findings.length > 0 && (
                        <div className="pt-2 border-t border-outline-variant/40 flex items-center gap-2 flex-wrap">
                          <span className="text-[10px] uppercase tracking-wider font-semibold text-outline">
                            Findings:
                          </span>
                          {selectedReq.findings.map((f) => {
                            const isFSelected = selectedFindingId === f.finding_id;
                            return (
                              <button
                                key={f.finding_id}
                                onClick={() => setSelectedFindingId(f.finding_id)}
                                className={`text-xs px-2 py-1 rounded-md transition-all flex items-center gap-1.5 ${
                                  isFSelected
                                    ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                                    : "bg-surface-container border border-outline-variant/60 text-on-surface-variant hover:text-on-surface"
                                }`}
                              >
                                <span>{f.finding_id}</span>
                                <span>•</span>
                                <span className="font-mono">{f.type.replace("CHECK_", "")}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>

                    {/* Quality Waterfall Breakdown */}
                    {selectedReq.waterfall_steps && selectedReq.waterfall_steps.length > 1 && (
                      <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/40">
                        <h4 className="text-xs font-bold text-on-surface mb-2 flex items-center gap-1.5">
                          <Shield className="w-3.5 h-3.5 text-primary" />
                          Deterministic Waterfall Deductions
                        </h4>
                        <div className="space-y-1.5">
                          {selectedReq.waterfall_steps.map((w, idx) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between text-xs py-1 border-b border-outline-variant/20 last:border-0"
                            >
                              <span className="text-on-surface-variant">{w.step_name}</span>
                              <div className="flex items-center gap-3">
                                {w.deduction > 0 && (
                                  <span className="text-rose-600 font-semibold font-mono">
                                    -{w.deduction}
                                  </span>
                                )}
                                <span className="font-mono font-medium text-on-surface">
                                  {w.current_score}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-on-surface-variant">Select a requirement from the left pane.</p>
                )
              ) : (
                /* Full Document Text Mode */
                <div className="p-4 rounded-xl bg-surface-container-low border border-outline-variant/40 font-mono text-xs text-on-surface leading-relaxed whitespace-pre-wrap">
                  {report.cleaned_text || report.raw_text}
                </div>
              )}
            </div>
          </div>

          {/* RIGHT PANE: Contextual Finding & Explanation Card (4 Cols) */}
          <div className="col-span-4 bg-surface-container-lowest flex flex-col h-full overflow-hidden">
            <div className="p-3 border-b border-outline-variant/40 bg-surface flex items-center justify-between">
              <span className="text-xs font-semibold text-on-surface">
                Finding Details & Explanation
              </span>
              {selectedFinding && (
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">
                  {selectedFinding.finding_id}
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {selectedFinding ? (
                <div className="space-y-4">
                  {/* Contextual Finding Header Card */}
                  <div className="p-4 rounded-xl bg-surface border border-outline-variant/40 shadow-xs space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-primary">
                        {selectedFinding.finding_id}
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                            selectedFinding.severity === "critical"
                              ? "bg-rose-100 text-rose-800"
                              : selectedFinding.severity === "warning"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-sky-100 text-sky-800"
                          }`}
                        >
                          {selectedFinding.severity}
                        </span>

                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
                            selectedFinding.confidence_band === "high"
                              ? "bg-emerald-100 text-emerald-800"
                              : selectedFinding.confidence_band === "medium"
                              ? "bg-amber-100 text-amber-800"
                              : "bg-slate-100 text-slate-800"
                          }`}
                          title="Confidence Band"
                        >
                          {selectedFinding.confidence !== null
                            ? `${Math.round(selectedFinding.confidence * 100)}% Conf`
                            : "Confidence N/A"}
                        </span>
                      </div>
                    </div>

                    <div>
                      <span className="text-[10px] font-medium text-outline uppercase tracking-wider block">
                        Issue Type & Rule
                      </span>
                      <p className="text-sm font-bold text-on-surface font-mono">
                        {selectedFinding.type}
                      </p>
                    </div>

                    {selectedFinding.spans && selectedFinding.spans.length > 0 && (
                      <div>
                        <span className="text-[10px] font-medium text-outline uppercase tracking-wider block">
                          Detected Exact Text
                        </span>
                        <code className="text-xs bg-surface-container px-2 py-1 rounded text-rose-900 font-mono block mt-1">
                          "{selectedFinding.spans.map((s) => s.text).join(", ")}"
                        </code>
                      </div>
                    )}
                  </div>

                  {/* Why it was highlighted (Human Explanation) */}
                  <div className="p-4 rounded-xl bg-surface border border-outline-variant/40 shadow-xs space-y-2">
                    <div className="flex items-center gap-1.5 text-xs font-bold text-on-surface">
                      <HelpCircle className="w-3.5 h-3.5 text-secondary" />
                      <span>Why This Is Highlighted</span>
                    </div>
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {selectedFinding.human_explanation}
                    </p>

                    <div className="pt-2 border-t border-outline-variant/20 flex items-center justify-between text-[11px] text-outline">
                      <span>Method Provenance:</span>
                      <span className="font-mono text-on-surface">{selectedFinding.rule_provenance}</span>
                    </div>
                  </div>

                  {/* Suggested Improvement */}
                  {selectedFinding.suggestion && (
                    <div className="p-4 rounded-xl bg-emerald-50/50 border border-emerald-200/60 shadow-xs space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-950">
                        <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                        <span>Suggested Improvement</span>
                      </div>
                      <p className="text-xs text-emerald-900 leading-relaxed font-sans">
                        {selectedFinding.suggestion}
                      </p>
                    </div>
                  )}

                  {/* Pair Findings (Duplicates / Contradictions) */}
                  {selectedFinding.is_pair_finding && selectedFinding.target_req_key && (
                    <div className="p-4 rounded-xl bg-sky-50/50 border border-sky-200/60 shadow-xs space-y-1.5">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-sky-950">
                        <Layers className="w-3.5 h-3.5 text-sky-600" />
                        <span>Paired Requirement</span>
                      </div>
                      <p className="text-xs text-sky-900">
                        Associated with target requirement: <strong>{selectedFinding.target_req_key}</strong>
                      </p>
                    </div>
                  )}

                  {/* Review Action & Cross Navigation Links */}
                  <div className="p-4 rounded-xl bg-surface border border-outline-variant/40 space-y-2">
                    <span className="text-[10px] font-medium text-outline uppercase tracking-wider block">
                      Auditor Navigation
                    </span>
                    <div className="flex flex-col gap-1.5">
                      <Link
                        href={`/requirements?doc=${selectedDocId}&req=${selectedFinding.requirement_id}`}
                        className="inline-flex items-center justify-between px-3 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-medium text-on-surface transition-colors"
                      >
                        <span>Open in Requirement Viewer</span>
                        <ExternalLink className="w-3.5 h-3.5 text-outline" />
                      </Link>

                      <Link
                        href={`/suggestions?doc=${selectedDocId}`}
                        className="inline-flex items-center justify-between px-3 py-2 rounded-lg bg-surface-container hover:bg-surface-container-high text-xs font-medium text-on-surface transition-colors"
                      >
                        <span>View AI Rewrite Suggestions</span>
                        <Sparkles className="w-3.5 h-3.5 text-outline" />
                      </Link>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-8 text-center text-on-surface-variant">
                  <Eye className="w-8 h-8 text-outline mx-auto mb-2 opacity-50" />
                  <p className="text-xs font-medium text-on-surface">No Finding Selected</p>
                  <p className="text-[11px] text-outline mt-1">
                    Click any highlighted phrase in the center pane or choose a requirement to inspect its findings.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function DetailedReviewReportPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading review report page..." />}>
      <DetailedReviewContent />
    </Suspense>
  );
}
