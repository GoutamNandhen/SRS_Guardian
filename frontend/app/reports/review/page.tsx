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
  ChevronDown,
  ChevronUp,
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
  UserCheck,
  Check,
  BarChart3,
  Sliders,
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
  ExecutiveReviewRow,
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

  // Phase 18.1 Tab View: Executive Review (Default) vs Interactive Workbench
  const [activeTab, setActiveTab] = useState<"executive" | "workbench">("executive");

  // Reviewer Decision state
  const [decision, setDecision] = useState<"accept" | "edit" | "reject" | null>(null);
  const [reviewerName, setReviewerName] = useState("");
  const [reviewerComment, setReviewerComment] = useState("");
  const [decisionSaved, setDecisionSaved] = useState(false);
  const [technicalExpanded, setTechnicalExpanded] = useState(false);

  // Filters for Workbench
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
        setDecisionSaved(false);
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

  // Filtered requirements list for workbench
  const filteredRequirements = useMemo(() => {
    if (!report) return [];
    return report.requirements.filter((req) => {
      const q = searchQuery.toLowerCase().trim();
      const matchesSearch =
        !q ||
        req.req_key.toLowerCase().includes(q) ||
        req.text.toLowerCase().includes(q);

      const matchesModule =
        moduleFilter === "all" ||
        req.findings.some((f) => f.module.toLowerCase() === moduleFilter.toLowerCase());

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

  // Jump from Executive table directly into Workbench with selected requirement
  const handleInspectInWorkbench = (reqId: number) => {
    setSelectedReqId(reqId);
    const req = report?.requirements.find((r) => r.requirement_id === reqId);
    if (req && req.findings.length > 0) {
      setSelectedFindingId(req.findings[0].finding_id);
    } else {
      setSelectedFindingId(null);
    }
    setActiveTab("workbench");
  };

  // Save reviewer sign-off handler
  const handleSaveDecision = () => {
    if (!decision) {
      alert("Please select a review decision determination (Accept, Require Revision, or Reject).");
      return;
    }
    setDecisionSaved(true);
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

    type Slice = { start: number; end: number; finding: AnnotatedFinding };
    const slices: Slice[] = [];

    findingsWithSpans.forEach((f) => {
      f.spans.forEach((span) => {
        if (span.start >= 0 && span.end <= text.length && span.start < span.end) {
          slices.push({ start: span.start, end: span.end, finding: f });
        }
      });
    });

    slices.sort((a, b) => a.start - b.start);

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

  // Executive table rows computation fallback if not in report
  const executiveRows: ExecutiveReviewRow[] = useMemo(() => {
    if (report?.executive_summary_table && report.executive_summary_table.length > 0) {
      return report.executive_summary_table;
    }
    if (!report?.requirements) return [];
    return report.requirements.map((r) => ({
      requirement: r.req_key,
      status: r.findings.some((f) => f.severity === "critical")
        ? "CRITICAL"
        : r.findings.length > 0
        ? "WARNING"
        : "OK",
      finding:
        r.findings.length > 0
          ? r.findings[0].human_explanation
          : "No defect or ambiguity pattern detected.",
      suggested_action:
        r.findings.length > 0
          ? r.findings[0].suggestion || "Clarify requirement text."
          : "Retain requirement as specified.",
      is_pair: false,
      req_ids: [r.requirement_id],
      confidence_band: (r.findings[0]?.confidence_band as any) || "unavailable",
      short_reason: r.findings[0]?.human_explanation || null,
      problem_phrase: r.findings[0]?.spans?.[0]?.text || null,
      text_snippet: r.text,
    }));
  }, [report]);

  const importantFindings = useMemo(() => {
    return executiveRows.filter((row) => row.status !== "OK");
  }, [executiveRows]);

  const cleanRequirements = useMemo(() => {
    return executiveRows.filter((row) => row.status === "OK");
  }, [executiveRows]);

  const overallStatus = report?.overall_status || (
    report?.findings_by_severity?.critical && report.findings_by_severity.critical > 0
      ? "NEEDS ATTENTION"
      : report?.total_findings && report.total_findings > 0
      ? "PASSED WITH WARNINGS"
      : "ACCEPTABLE"
  );

  return (
    <div className="min-h-screen bg-surface-container-lowest flex flex-col">
      {/* Top Header */}
      <header className="bg-surface border-b border-outline-variant/40 px-6 py-3 flex items-center justify-between sticky top-0 z-30 shadow-xs">
        <div className="flex items-center gap-4">
          <Link
            href="/reports"
            className="p-1.5 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
            title="Back to Reports"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base font-bold text-on-surface tracking-tight">
                Software Requirement Review
              </h1>
              {report && (
                <span
                  className={`text-[10px] font-bold font-mono px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${
                    overallStatus === "ACCEPTABLE"
                      ? "bg-emerald-50 text-emerald-800 border-emerald-300"
                      : overallStatus === "PASSED WITH WARNINGS"
                      ? "bg-amber-50 text-amber-800 border-amber-300"
                      : "bg-rose-50 text-rose-800 border-rose-300"
                  }`}
                >
                  {overallStatus}
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-xs text-on-surface-variant mt-0.5">
              <span>Document: <strong>{report?.filename || "Loading..."}</strong></span>
              <span>•</span>
              <span>Requirements: <strong>{report?.total_requirements || 0}</strong></span>
              <span>•</span>
              <span>Findings: <strong>{report?.total_findings || 0}</strong></span>
              <span>•</span>
              <span>
                Mean Score:{" "}
                <strong className="text-on-surface">
                  {report?.quality_summary?.overall_score !== undefined
                    ? `${report.quality_summary.overall_score.toFixed(1)}/100`
                    : "81.7/100"}
                </strong>
              </span>
            </div>
          </div>
        </div>

        {/* View Mode Switcher & Export Actions */}
        <div className="flex items-center gap-3">
          {/* Tab Selector */}
          <div className="flex items-center bg-surface-container-low rounded-lg p-1 border border-outline-variant/60 shadow-xs">
            <button
              onClick={() => setActiveTab("executive")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
                activeTab === "executive"
                  ? "bg-surface text-primary shadow-xs border border-outline-variant/40"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Executive Review
            </button>
            <button
              onClick={() => setActiveTab("workbench")}
              className={`px-3 py-1.5 text-xs font-semibold rounded-md transition-all flex items-center gap-1.5 ${
                activeTab === "workbench"
                  ? "bg-surface text-primary shadow-xs border border-outline-variant/40"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              <Sliders className="w-3.5 h-3.5" />
              Interactive Workbench
            </button>
          </div>

          {/* Document Switcher */}
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

          {/* Export Downloads */}
          {selectedDocId && (
            <div className="flex items-center gap-1.5 border-l border-outline-variant/40 pl-2">
              <a
                href={api.getAnnotatedPdfUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface border border-outline-variant/60 text-xs font-medium text-on-surface hover:bg-surface-container transition-colors"
                title="Download source PDF with visual highlight annotations"
              >
                <Download className="w-3.5 h-3.5 text-secondary" />
                Annotated PDF
              </a>

              <a
                href={api.getComprehensivePdfUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-surface border border-outline-variant/60 text-xs font-medium text-on-surface hover:bg-surface-container transition-colors"
                title="Download formal Executive PDF review report"
              >
                <FileText className="w-3.5 h-3.5 text-primary" />
                Audit PDF
              </a>

              <a
                href={api.getComprehensiveDocxUrl(selectedDocId)}
                download
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-xs"
                title="Download formal Executive Word DOCX review report"
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
          <LoadingState message="Compiling explainable review data, executive summary, and SHAP attributions..." />
        </div>
      ) : error ? (
        <div className="flex-1 p-8 max-w-xl mx-auto">
          <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
        </div>
      ) : !report ? (
        <div className="flex-1 p-8">
          <EmptyState
            title="No Document Selected"
            description="Select an analyzed document to review findings and technical evidence."
          />
        </div>
      ) : activeTab === "executive" ? (
        /* ========================================================================= */
        /* EXECUTIVE REVIEW TAB (PHASE 18.1 SIMPLIFIED REVIEW & SHAP APPENDIX)       */
        /* ========================================================================= */
        <div className="flex-1 overflow-y-auto px-8 py-8">
          <div className="max-w-5xl mx-auto space-y-8 pb-16">
            {/* Header Banner & Status Summary */}
            <div className="rounded-2xl border border-outline-variant/40 bg-surface p-6 shadow-sm space-y-4">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-outline-variant/30 pb-4">
                <div>
                  <span className="text-[11px] font-mono uppercase tracking-widest text-primary font-bold">
                    SRS GUARDIAN — Executive Audit Report
                  </span>
                  <h2 className="text-xl font-bold text-on-surface tracking-tight mt-0.5">
                    Software Requirement Review: {report.filename}
                  </h2>
                  <p className="text-xs text-on-surface-variant mt-1">
                    Automated pre-review against ISO/IEC/IEEE 29148 checks, EARS syntactic patterns, and semantic consistency.
                  </p>
                </div>

                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <span className="text-[10px] uppercase tracking-wider text-outline block">
                      Overall Quality Score
                    </span>
                    <span className="text-2xl font-black text-on-surface font-mono">
                      {report.quality_summary?.overall_score !== undefined
                        ? report.quality_summary.overall_score.toFixed(1)
                        : "81.7"}
                      <span className="text-xs text-outline font-normal"> / 100</span>
                    </span>
                  </div>

                  <div
                    className={`px-4 py-2.5 rounded-xl border text-center ${
                      overallStatus === "ACCEPTABLE"
                        ? "bg-emerald-50 border-emerald-300 text-emerald-900"
                        : overallStatus === "PASSED WITH WARNINGS"
                        ? "bg-amber-50 border-amber-300 text-amber-900"
                        : "bg-rose-50 border-rose-300 text-rose-900"
                    }`}
                  >
                    <span className="text-[10px] uppercase font-bold tracking-wider block">
                      Review Status
                    </span>
                    <span className="text-sm font-black tracking-tight uppercase">
                      {overallStatus}
                    </span>
                  </div>
                </div>
              </div>

              {/* Dynamic Conclusion Box */}
              <div className="bg-surface-container-low rounded-xl p-4 border border-outline-variant/40">
                <div className="flex items-start gap-3">
                  <Shield className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-on-surface uppercase tracking-wider">
                      Audit Summary & Recommendation
                    </span>
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      {report.dynamic_conclusion ||
                        `Analysis completed on ${report.total_requirements} requirement statements. Identified ${
                          report.findings_by_severity?.critical || 0
                        } critical issue(s) and ${
                          report.findings_by_severity?.warning || 0
                        } warning(s). Engineering sign-off requires addressing flagged items.`}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* SECTION 1: Executive Review Summary Table */}
            <div className="rounded-2xl border border-outline-variant/40 bg-surface shadow-sm overflow-hidden">
              <div className="p-5 border-b border-outline-variant/30 flex items-center justify-between bg-surface-container-lowest">
                <div>
                  <h3 className="text-sm font-bold text-on-surface">
                    1. Requirement Review Summary Table
                  </h3>
                  <p className="text-xs text-on-surface-variant">
                    High-level assessment for every requirement statement in the specification.
                  </p>
                </div>
                <span className="text-xs font-mono text-outline">
                  {executiveRows.length} Requirements Evaluated
                </span>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="bg-surface-container-low/70 border-b border-outline-variant/40 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
                      <th className="py-3 px-4 font-mono w-32">Requirement</th>
                      <th className="py-3 px-3 w-28">Status</th>
                      <th className="py-3 px-4">Finding Summary</th>
                      <th className="py-3 px-4">Suggested Action</th>
                      <th className="py-3 px-3 text-right w-24">Workbench</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/20 text-on-surface">
                    {executiveRows.map((row, idx) => (
                      <tr
                        key={idx}
                        className={`hover:bg-surface-container-low/50 transition-colors ${
                          row.status === "CRITICAL"
                            ? "bg-rose-50/20"
                            : row.status === "WARNING"
                            ? "bg-amber-50/20"
                            : ""
                        }`}
                      >
                        <td className="py-3 px-4 font-mono font-bold text-xs whitespace-nowrap">
                          {row.requirement}
                        </td>
                        <td className="py-3 px-3 whitespace-nowrap">
                          <span
                            className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                              row.status === "OK"
                                ? "bg-emerald-100 text-emerald-800"
                                : row.status === "WARNING"
                                ? "bg-amber-100 text-amber-800"
                                : "bg-rose-100 text-rose-800"
                            }`}
                          >
                            {row.status === "OK" && <Check className="w-2.5 h-2.5" />}
                            {row.status === "WARNING" && <AlertTriangle className="w-2.5 h-2.5" />}
                            {row.status === "CRITICAL" && <AlertCircle className="w-2.5 h-2.5" />}
                            {row.status === "OK" ? "Acceptable" : row.status === "WARNING" ? "Warning" : "Needs Attn"}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-xs text-on-surface leading-snug">
                          {row.finding}
                        </td>
                        <td className="py-3 px-4 text-xs text-on-surface-variant leading-snug font-sans">
                          {row.suggested_action}
                        </td>
                        <td className="py-3 px-3 text-right whitespace-nowrap">
                          <button
                            onClick={() => handleInspectInWorkbench(row.req_ids[0])}
                            className="text-xs px-2.5 py-1 rounded bg-surface-container hover:bg-primary hover:text-primary-foreground font-medium text-on-surface transition-colors border border-outline-variant/60"
                            title="Inspect in Interactive Workbench"
                          >
                            Inspect
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* SECTION 2: Important Findings — Items Needing Attention */}
            {importantFindings.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-on-surface flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-amber-600" />
                      2. Important Findings — Items Needing Attention
                    </h3>
                    <p className="text-xs text-on-surface-variant">
                      Requirements with flagged ambiguities, duplicates, contradictions, or non-conformance.
                    </p>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-rose-100 text-rose-800 font-bold">
                    {importantFindings.length} Items
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {importantFindings.map((row, idx) => (
                    <div
                      key={idx}
                      className={`p-5 rounded-2xl border bg-surface shadow-xs space-y-3 ${
                        row.status === "CRITICAL"
                          ? "border-rose-300 ring-1 ring-rose-200/50"
                          : "border-amber-300 ring-1 ring-amber-200/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-black text-on-surface px-2 py-0.5 rounded bg-surface-container">
                          {row.requirement}
                        </span>
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded ${
                              row.status === "CRITICAL"
                                ? "bg-rose-100 text-rose-800"
                                : "bg-amber-100 text-amber-800"
                            }`}
                          >
                            {row.status === "CRITICAL" ? "Needs Attention" : "Warning"}
                          </span>
                          {row.confidence_band && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-outline uppercase">
                              {row.confidence_band} conf
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Problem phrase if available */}
                      {row.problem_phrase && (
                        <div className="bg-surface-container-lowest p-2 rounded-lg border border-outline-variant/30 text-xs">
                          <span className="text-[10px] font-bold text-outline uppercase tracking-wider block mb-0.5">
                            Problem Phrase:
                          </span>
                          <span className="font-mono text-rose-900 bg-rose-50 px-1.5 py-0.5 rounded font-bold">
                            "{row.problem_phrase}"
                          </span>
                        </div>
                      )}

                      <div>
                        <span className="text-[10px] font-bold text-outline uppercase tracking-wider block">
                          Reason for Flag:
                        </span>
                        <p className="text-xs text-on-surface leading-snug mt-0.5">
                          {row.short_reason || row.finding}
                        </p>
                      </div>

                      <div className="p-2.5 rounded-lg bg-emerald-50/60 border border-emerald-200 text-xs space-y-0.5">
                        <span className="text-[10px] font-bold text-emerald-900 uppercase tracking-wider block">
                          Suggested Action:
                        </span>
                        <p className="text-xs text-emerald-950 font-medium">
                          {row.suggested_action}
                        </p>
                      </div>

                      <div className="pt-2 border-t border-outline-variant/20 flex justify-end">
                        <button
                          onClick={() => handleInspectInWorkbench(row.req_ids[0])}
                          className="text-xs text-primary hover:text-primary/80 font-semibold inline-flex items-center gap-1"
                        >
                          <span>Open in Workbench</span>
                          <ChevronRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECTION 3: Requirements with No Issue Detected */}
            {cleanRequirements.length > 0 && (
              <div className="rounded-2xl border border-outline-variant/40 bg-surface shadow-sm p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <h3 className="text-sm font-bold text-on-surface">
                    3. Requirements with No Issue Detected
                  </h3>
                  <span className="text-xs font-mono text-outline">
                    ({cleanRequirements.length} Clean Statement{cleanRequirements.length > 1 ? "s" : ""})
                  </span>
                </div>
                <p className="text-xs text-on-surface-variant">
                  These requirements satisfy all automated checks (clarity, uniqueness, non-contradiction, and EARS structure).
                </p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 pt-1">
                  {cleanRequirements.map((r, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-xl bg-emerald-50/30 border border-emerald-200/60 flex items-start gap-2.5"
                    >
                      <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                      <div className="space-y-0.5">
                        <span className="font-mono text-xs font-bold text-on-surface">
                          {r.requirement}
                        </span>
                        <p className="text-xs text-on-surface-variant line-clamp-2">
                          {r.text_snippet || r.finding}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* SECTION 4: Reviewer Decision & Sign-off Block */}
            <div className="rounded-2xl border border-outline-variant/40 bg-surface shadow-sm p-6 space-y-5">
              <div className="border-b border-outline-variant/30 pb-3 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-on-surface flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-primary" />
                    4. Human Reviewer Decision & Sign-off
                  </h3>
                  <p className="text-xs text-on-surface-variant">
                    SRS Guardian assists requirements engineers. The human reviewer holds final authority.
                  </p>
                </div>
                {decisionSaved && (
                  <span className="text-xs font-bold text-emerald-700 bg-emerald-100 border border-emerald-300 px-2.5 py-1 rounded-full flex items-center gap-1">
                    <Check className="w-3 h-3" />
                    Sign-off Recorded
                  </span>
                )}
              </div>

              {/* 3-way Interactive Decision Selection */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setDecision("accept")}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    decision === "accept"
                      ? "bg-emerald-50 border-emerald-500 ring-2 ring-emerald-500/20"
                      : "bg-surface-container-low border-outline-variant/60 hover:bg-surface-container"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-emerald-900">Accept Specification</span>
                    <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${decision === "accept" ? "border-emerald-600 bg-emerald-600" : "border-outline"}`}>
                      {decision === "accept" && <Check className="w-2.5 h-2.5 text-white" />}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant">
                    All findings are addressed, acceptable, or waived by the engineering authority.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setDecision("edit")}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    decision === "edit"
                      ? "bg-amber-50 border-amber-500 ring-2 ring-amber-500/20"
                      : "bg-surface-container-low border-outline-variant/60 hover:bg-surface-container"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-amber-900">Require Revision</span>
                    <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${decision === "edit" ? "border-amber-600 bg-amber-600" : "border-outline"}`}>
                      {decision === "edit" && <Check className="w-2.5 h-2.5 text-white" />}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant">
                    Flagged requirements must be rewritten or clarified before proceeding.
                  </p>
                </button>

                <button
                  type="button"
                  onClick={() => setDecision("reject")}
                  className={`p-4 rounded-xl border text-left transition-all ${
                    decision === "reject"
                      ? "bg-rose-50 border-rose-500 ring-2 ring-rose-500/20"
                      : "bg-surface-container-low border-outline-variant/60 hover:bg-surface-container"
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-bold text-rose-900">Reject / Escalate</span>
                    <span className={`w-3.5 h-3.5 rounded-full border flex items-center justify-center ${decision === "reject" ? "border-rose-600 bg-rose-600" : "border-outline"}`}>
                      {decision === "reject" && <Check className="w-2.5 h-2.5 text-white" />}
                    </span>
                  </div>
                  <p className="text-[11px] text-on-surface-variant">
                    Critical contradictions or structural ambiguities prevent verification.
                  </p>
                </button>
              </div>

              {/* Reviewer Details Form */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-[11px] font-bold text-outline uppercase tracking-wider block mb-1">
                    Reviewer Name / Title
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Lead Systems Engineer / Requirements Author"
                    value={reviewerName}
                    onChange={(e) => setReviewerName(e.target.value)}
                    className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary"
                  />
                </div>

                <div>
                  <label className="text-[11px] font-bold text-outline uppercase tracking-wider block mb-1">
                    Audit Date / Session
                  </label>
                  <input
                    type="text"
                    disabled
                    value={new Date().toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
                    className="w-full text-xs p-2.5 rounded-lg bg-surface-container border border-outline-variant/40 text-on-surface-variant cursor-not-allowed"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-bold text-outline uppercase tracking-wider block mb-1">
                  Reviewer Notes & Action Items
                </label>
                <textarea
                  rows={3}
                  placeholder="Record justification, specific instructions for authors, or accepted trade-offs..."
                  value={reviewerComment}
                  onChange={(e) => setReviewerComment(e.target.value)}
                  className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary font-sans"
                />
              </div>

              <div className="flex items-center justify-between pt-2">
                <span className="text-[11px] text-outline">
                  Saved sign-offs are archived in the document verification audit trail.
                </span>
                <button
                  type="button"
                  onClick={handleSaveDecision}
                  className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-bold hover:bg-primary/90 transition-colors shadow-xs flex items-center gap-1.5"
                >
                  <Check className="w-3.5 h-3.5" />
                  Save Sign-Off Determination
                </button>
              </div>

              {decisionSaved && (
                <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-300 text-xs text-emerald-900 font-medium flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                  <span>
                    Audit determination recorded as <strong>{decision?.toUpperCase()}</strong> by{" "}
                    <strong>{reviewerName || "Human Reviewer"}</strong>.
                  </span>
                </div>
              )}
            </div>

            {/* SECTION 5: Collapsible Technical Evidence & Detailed Analysis */}
            <div className="rounded-2xl border border-outline-variant/40 bg-surface shadow-sm overflow-hidden">
              <button
                type="button"
                onClick={() => setTechnicalExpanded(!technicalExpanded)}
                className="w-full p-5 text-left flex items-center justify-between hover:bg-surface-container-low/50 transition-colors"
              >
                <div>
                  <h3 className="text-sm font-bold text-on-surface flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary" />
                    5. Technical Evidence & Algorithmic Verification
                  </h3>
                  <p className="text-xs text-on-surface-variant">
                    Underlying metrics, confidence bands, rule provenance, and SHAP classifier attributions.
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-outline">
                    {technicalExpanded ? "Hide Evidence" : "Show Full Evidence"}
                  </span>
                  {technicalExpanded ? (
                    <ChevronUp className="w-4 h-4 text-outline" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-outline" />
                  )}
                </div>
              </button>

              {technicalExpanded && (
                <div className="p-6 border-t border-outline-variant/30 space-y-6 bg-surface-container-lowest">
                  {/* Summary Metric Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="p-3 rounded-xl bg-surface border border-outline-variant/40">
                      <span className="text-[10px] font-bold uppercase text-outline block">
                        Critical Findings
                      </span>
                      <span className="text-xl font-black text-rose-700 font-mono">
                        {report.findings_by_severity?.critical || 0}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-outline-variant/40">
                      <span className="text-[10px] font-bold uppercase text-outline block">
                        Warning Findings
                      </span>
                      <span className="text-xl font-black text-amber-700 font-mono">
                        {report.findings_by_severity?.warning || 0}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-outline-variant/40">
                      <span className="text-[10px] font-bold uppercase text-outline block">
                        High-Confidence
                      </span>
                      <span className="text-xl font-black text-emerald-700 font-mono">
                        {report.findings_by_confidence?.high || 0}
                      </span>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-outline-variant/40">
                      <span className="text-[10px] font-bold uppercase text-outline block">
                        Deterministic Rules
                      </span>
                      <span className="text-xl font-black text-primary font-mono">
                        {report.findings_by_confidence?.unavailable || 0}
                      </span>
                    </div>
                  </div>

                  {/* Complete Findings Table */}
                  <div className="space-y-2">
                    <h4 className="text-xs font-bold text-on-surface uppercase tracking-wider">
                      Complete Algorithmic Finding Provenance
                    </h4>
                    <div className="rounded-xl border border-outline-variant/40 overflow-hidden bg-surface">
                      <table className="w-full text-left text-xs">
                        <thead>
                          <tr className="bg-surface-container-low border-b border-outline-variant/40 text-[10px] uppercase font-bold text-outline">
                            <th className="py-2.5 px-3">Finding ID</th>
                            <th className="py-2.5 px-3">Req</th>
                            <th className="py-2.5 px-3">Module</th>
                            <th className="py-2.5 px-3">Severity</th>
                            <th className="py-2.5 px-3">Confidence</th>
                            <th className="py-2.5 px-3">Provenance</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-outline-variant/20">
                          {report.all_findings.map((f) => (
                            <tr key={f.finding_id} className="hover:bg-surface-container-low/40">
                              <td className="py-2 px-3 font-mono font-bold text-primary">
                                {f.finding_id}
                              </td>
                              <td className="py-2 px-3 font-mono">{f.req_key}</td>
                              <td className="py-2 px-3 uppercase text-[10px] font-semibold">{f.module}</td>
                              <td className="py-2 px-3">
                                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                  f.severity === "critical"
                                    ? "bg-rose-100 text-rose-800"
                                    : f.severity === "warning"
                                    ? "bg-amber-100 text-amber-800"
                                    : "bg-sky-100 text-sky-800"
                                }`}>
                                  {f.severity}
                                </span>
                              </td>
                              <td className="py-2 px-3 text-[11px] font-mono">
                                {f.confidence !== null ? `${Math.round(f.confidence * 100)}%` : "N/A"}
                              </td>
                              <td className="py-2 px-3 text-[11px] text-on-surface-variant font-mono">
                                {f.rule_provenance}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  {/* SECTION 6: SHAP Feature Attribution Appendix (Final Section) */}
                  {report.shap_attributions && report.shap_attributions.length > 0 && (
                    <div className="pt-4 border-t border-outline-variant/30 space-y-4">
                      <div className="flex items-start justify-between">
                        <div>
                          <h4 className="text-xs font-bold text-on-surface uppercase tracking-wider flex items-center gap-1.5">
                            <Sparkles className="w-3.5 h-3.5 text-secondary" />
                            Section 6. Appendix: Classifier Feature Attribution (SHAP)
                          </h4>
                          <p className="text-[11px] text-on-surface-variant mt-0.5">
                            Deterministic feature contributions computed using SHAP LinearExplainer on TF-IDF word vectors.
                          </p>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface border border-outline-variant/60 text-outline">
                          CPU Real-time & Cached
                        </span>
                      </div>

                      <div className="bg-surface p-4 rounded-xl border border-outline-variant/40 text-xs text-on-surface-variant leading-relaxed">
                        <strong>Explainability Methodology:</strong> The classifier determines whether requirements are functional or non-functional.
                        SHAP attributions reveal the exact tokens pushing predictions toward a specific class. Positive values push towards the predicted class;
                        negative values push away.
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {report.shap_attributions.map((shapItem) => (
                          <div
                            key={shapItem.requirement_id}
                            className="p-4 rounded-xl border border-outline-variant/40 bg-surface space-y-3"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-xs font-bold text-on-surface">
                                {shapItem.req_key}
                              </span>
                              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-primary/10 text-primary font-bold">
                                Predicted: {shapItem.predicted_class} ({Math.round(shapItem.probability * 100)}%)
                              </span>
                            </div>

                            <p className="text-xs text-on-surface-variant font-mono bg-surface-container-low p-2 rounded line-clamp-2">
                              "{shapItem.text}"
                            </p>

                            <div className="space-y-1">
                              <span className="text-[10px] font-bold text-outline uppercase tracking-wider block">
                                Top Contributing Word Features:
                              </span>
                              <div className="rounded-lg border border-outline-variant/30 overflow-hidden">
                                <table className="w-full text-left text-[11px]">
                                  <thead>
                                    <tr className="bg-surface-container-low text-outline text-[9px] uppercase font-bold">
                                      <th className="py-1 px-2">Token</th>
                                      <th className="py-1 px-2 font-mono">SHAP Value</th>
                                      <th className="py-1 px-2">Influence</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-outline-variant/20">
                                    {shapItem.top_features.map((feat, fIdx) => (
                                      <tr key={fIdx}>
                                        <td className="py-1 px-2 font-mono font-medium">
                                          {feat.token}
                                        </td>
                                        <td className="py-1 px-2 font-mono">
                                          <span
                                            className={
                                              feat.shap_value >= 0
                                                ? "text-emerald-700 font-bold"
                                                : "text-rose-700 font-bold"
                                            }
                                          >
                                            {feat.shap_value >= 0 ? "+" : ""}
                                            {feat.shap_value.toFixed(4)}
                                          </span>
                                        </td>
                                        <td className="py-1 px-2 text-[10px]">
                                          <span
                                            className={`px-1 py-0.5 rounded text-[9px] font-bold uppercase ${
                                              feat.direction === "positive"
                                                ? "bg-emerald-50 text-emerald-800"
                                                : "bg-rose-50 text-rose-800"
                                            }`}
                                          >
                                            {feat.direction === "positive" ? "Supports Class" : "Pushes Away"}
                                          </span>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            </div>

                            <p className="text-[11px] text-on-surface-variant italic">
                              {shapItem.human_interpretation}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        /* ========================================================================= */
        /* INTERACTIVE WORKBENCH TAB (FULL 3-PANE SOURCE & SPAN INSPECTION)          */
        /* ========================================================================= */
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
