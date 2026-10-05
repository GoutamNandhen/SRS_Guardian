"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Search,
  Filter,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Info,
  Layers,
  ChevronDown,
  Copy,
  Edit3,
  Check,
  X,
  Sparkles,
  BarChart3,
  ListOrdered,
  FileText,
  Activity,
  ArrowUpDown,
} from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  Requirement,
  RequirementDetail,
  Issue,
  ShapToken,
  RewriteSuggestionResponse,
  GherkinGenerationResponse,
} from "@/types";

function RequirementViewerContent() {
  const searchParams = useSearchParams();
  const initialDocParam = searchParams.get("doc");

  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(
    initialDocParam ? parseInt(initialDocParam, 10) : null
  );

  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [selectedReqId, setSelectedReqId] = useState<number | null>(null);
  const [reqDetail, setReqDetail] = useState<RequirementDetail | null>(null);

  const [loadingDocs, setLoadingDocs] = useState(true);
  const [loadingReqs, setLoadingReqs] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters & Search
  const [searchQuery, setSearchQuery] = useState("");
  const [classFilter, setClassFilter] = useState<"ALL" | "Functional" | "Non-Functional">("ALL");
  const [scoreFilter, setScoreFilter] = useState<"ALL" | "HIGH" | "MED" | "LOW">("ALL");

  // Inline editing state for human review
  const [editingIssueId, setEditingIssueId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [reviewNotice, setReviewNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // Copy ID feedback
  const [copiedId, setCopiedId] = useState(false);

  // AI Assistance (Phase 14)
  const [loadingRewrite, setLoadingRewrite] = useState(false);
  const [rewriteResult, setRewriteResult] = useState<RewriteSuggestionResponse | null>(null);
  const [loadingGherkin, setLoadingGherkin] = useState(false);
  const [gherkinResult, setGherkinResult] = useState<GherkinGenerationResponse | null>(null);
  const [activeAiTab, setActiveAiTab] = useState<"none" | "rewrite" | "gherkin">("none");
  const [copiedGherkin, setCopiedGherkin] = useState(false);

  // Clear AI results when selected requirement changes
  useEffect(() => {
    setRewriteResult(null);
    setGherkinResult(null);
    setActiveAiTab("none");
  }, [selectedReqId]);

  async function handleSuggestRewrite() {
    if (!selectedReqId) return;
    try {
      setLoadingRewrite(true);
      setActiveAiTab("rewrite");
      const res = await api.suggestRewrite(selectedReqId);
      setRewriteResult(res);
    } catch (err: any) {
      setRewriteResult({
        enabled: true,
        cached: false,
        original_text: reqDetail?.text || "",
        error: err.message || "Failed to generate rewrite suggestion",
        changes_made: [],
        conforms_to_ears: false,
      });
    } finally {
      setLoadingRewrite(false);
    }
  }

  async function handleGenerateGherkin() {
    if (!selectedReqId) return;
    try {
      setLoadingGherkin(true);
      setActiveAiTab("gherkin");
      const res = await api.generateGherkin(selectedReqId);
      setGherkinResult(res);
    } catch (err: any) {
      setGherkinResult({
        enabled: true,
        cached: false,
        requirement_text: reqDetail?.text || "",
        error: err.message || "Failed to generate Gherkin scenarios",
      });
    } finally {
      setLoadingGherkin(false);
    }
  }

  // 1. Fetch available documents
  useEffect(() => {
    async function loadDocs() {
      try {
        setLoadingDocs(true);
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length > 0) {
          if (!selectedDocId || !docs.some((d) => d.id === selectedDocId)) {
            setSelectedDocId(docs[0].id);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load documents");
      } finally {
        setLoadingDocs(false);
      }
    }
    loadDocs();
  }, []);

  // 2. Fetch requirements when selected document changes
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadRequirements() {
      try {
        setLoadingReqs(true);
        setError(null);
        const reqs = await api.getDocumentRequirements(selectedDocId!);
        setRequirements(reqs);
        if (reqs.length > 0) {
          setSelectedReqId(reqs[0].id);
        } else {
          setSelectedReqId(null);
          setReqDetail(null);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load requirements for selected document");
      } finally {
        setLoadingReqs(false);
      }
    }
    loadRequirements();
  }, [selectedDocId]);

  // 3. Fetch detailed requirement info (scores, waterfall, issues) when selectedReqId changes
  const fetchRequirementDetail = async (reqId: number) => {
    try {
      setLoadingDetail(true);
      const detail = await api.getRequirement(reqId);
      setReqDetail(detail);
      setEditText(detail.text);
    } catch (err: any) {
      console.error("Failed to load requirement detail", err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    if (selectedReqId) {
      fetchRequirementDetail(selectedReqId);
      setEditingIssueId(null);
    }
  }, [selectedReqId]);

  // Handle Review Actions (Accept / Reject / Edit)
  const handleReview = async (issueId: number, action: "accept" | "reject" | "edit") => {
    try {
      setReviewNotice(null);
      await api.reviewIssue(issueId, {
        action,
        edited_text: action === "edit" ? editText : undefined,
        note: action === "edit" ? "User edited requirement text directly." : undefined,
      });

      setReviewNotice({
        type: "success",
        message: `Finding marked as ${action.toUpperCase()} successfully.`,
      });

      // Reload detail and list
      if (selectedReqId) {
        await fetchRequirementDetail(selectedReqId);
      }
      if (selectedDocId) {
        const reqs = await api.getDocumentRequirements(selectedDocId);
        setRequirements(reqs);
      }
      setEditingIssueId(null);
    } catch (err: any) {
      setReviewNotice({
        type: "error",
        message: `Review action failed: ${err.message || "Unknown error"}`,
      });
    }
  };

  // Filter requirements
  const filteredRequirements = useMemo(() => {
    return requirements.filter((r) => {
      const matchSearch =
        r.req_key.toLowerCase().includes(searchQuery.toLowerCase()) ||
        r.text.toLowerCase().includes(searchQuery.toLowerCase());

      const matchClass =
        classFilter === "ALL" || r.classification_label === classFilter;

      return matchSearch && matchClass;
    });
  }, [requirements, searchQuery, classFilter]);

  // Format SHAP tokens if available
  const shapTokens: ShapToken[] = useMemo(() => {
    if (!reqDetail || !reqDetail.classification_explanation) return [];
    if (Array.isArray(reqDetail.classification_explanation)) {
      return reqDetail.classification_explanation as ShapToken[];
    }
    return [];
  }, [reqDetail]);

  const copyReqId = () => {
    if (!reqDetail) return;
    navigator.clipboard.writeText(reqDetail.req_key);
    setCopiedId(true);
    setTimeout(() => setCopiedId(false), 2000);
  };

  const getScoreColor = (score: number | undefined) => {
    if (score === undefined) return "text-outline bg-surface-container";
    if (score >= 80) return "text-emerald-700 bg-emerald-50 border-emerald-200";
    if (score >= 60) return "text-amber-700 bg-amber-50 border-amber-200";
    return "text-rose-700 bg-rose-50 border-rose-200";
  };

  const getScoreBarColor = (score: number | undefined) => {
    if (score === undefined) return "bg-outline";
    if (score >= 80) return "bg-emerald-600";
    if (score >= 60) return "bg-amber-600";
    return "bg-rose-600";
  };

  // Highlight problematic words in the statement
  const renderHighlightedStatement = (text: string, issues: Issue[]) => {
    // Extract unique problematic terms from issue explanation spans or suggestions
    const terms: { term: string; explanation: string; severity: string }[] = [];

    issues.forEach((issue) => {
      const exp = issue.explanation as any;
      if (exp?.spans && Array.isArray(exp.spans)) {
        exp.spans.forEach((span: any) => {
          if (span.text && !terms.some((t) => t.term.toLowerCase() === span.text.toLowerCase())) {
            terms.push({
              term: span.text,
              explanation: exp.human_explanation || issue.type,
              severity: issue.severity,
            });
          }
        });
      }
    });

    if (terms.length === 0) {
      return <span>{text}</span>;
    }

    // Split text with regex pattern matching any of the terms
    const regex = new RegExp(`\\b(${terms.map((t) => t.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})\\b`, "gi");
    const parts = text.split(regex);

    return (
      <span>
        {parts.map((part, idx) => {
          const matched = terms.find((t) => t.term.toLowerCase() === part.toLowerCase());
          if (matched) {
            return (
              <span
                key={idx}
                title={`${matched.severity.toUpperCase()}: ${matched.explanation}`}
                className="mx-0.5 px-1.5 py-0.5 rounded font-medium bg-amber-100 text-amber-900 border-b-2 border-amber-500 cursor-help"
              >
                {part}
              </span>
            );
          }
          return <span key={idx}>{part}</span>;
        })}
      </span>
    );
  };

  return (
    <div className="flex flex-col gap-4 max-w-7xl mx-auto w-full">
      {/* Top Header & Document Context Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/50 shadow-xs">
        {/* Left: Document Picker */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-outline" />
            <span className="text-xs font-semibold text-outline uppercase tracking-wider">
              Document:
            </span>
          </div>

          <div className="relative">
            <select
              value={selectedDocId || ""}
              onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
              className="h-8 pl-3 pr-8 rounded-lg bg-surface-container-low border border-outline-variant/60 text-xs font-semibold text-on-surface focus:outline-none focus:border-secondary transition-colors cursor-pointer appearance-none"
            >
              {documents.map((doc) => (
                <option key={doc.id} value={doc.id}>
                  {doc.filename} ({doc.requirement_count ?? doc.requirements_count ?? 0} reqs)
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-outline absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          <div className="hidden sm:flex items-center gap-2 text-xs text-outline font-mono">
            <span>•</span>
            <span>{requirements.length} total requirements</span>
          </div>
        </div>

        {/* Right: Search & Classification Filter */}
        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative flex items-center w-52 h-8 px-2.5 rounded-lg bg-surface-container-low border border-outline-variant/60 focus-within:border-secondary transition-all">
            <Search className="w-3.5 h-3.5 text-outline mr-1.5 flex-shrink-0" />
            <input
              type="text"
              placeholder="Search in document..."
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

          <div className="flex items-center rounded-lg bg-surface-container-low p-0.5 border border-outline-variant/60">
            <button
              onClick={() => setClassFilter("ALL")}
              className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                classFilter === "ALL"
                  ? "bg-surface-container-lowest text-on-surface font-semibold shadow-xs"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setClassFilter("Functional")}
              className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                classFilter === "Functional"
                  ? "bg-surface-container-lowest text-on-surface font-semibold shadow-xs"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Functional
            </button>
            <button
              onClick={() => setClassFilter("Non-Functional")}
              className={`px-2.5 py-1 text-[11px] font-medium rounded ${
                classFilter === "Non-Functional"
                  ? "bg-surface-container-lowest text-on-surface font-semibold shadow-xs"
                  : "text-on-surface-variant hover:text-on-surface"
              }`}
            >
              Non-Functional
            </button>
          </div>
        </div>
      </div>

      {/* Review Feedback Banner */}
      {reviewNotice && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
            reviewNotice.type === "success"
              ? "bg-emerald-50 text-emerald-900 border-emerald-200"
              : "bg-rose-50 text-rose-900 border-rose-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {reviewNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span>{reviewNotice.message}</span>
          </div>
          <button
            onClick={() => setReviewNotice(null)}
            className="text-xs opacity-60 hover:opacity-100 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Split View: Left (List 55%) & Right (Inspection 45%) */}
      {loadingDocs || loadingReqs ? (
        <LoadingState message="Loading requirements..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
      ) : requirements.length === 0 ? (
        <EmptyState
          title="No requirements found in this specification"
          description="Click 'Analyze' in the Documents tab to extract and evaluate requirements from this document."
          actionLabel="Go to Documents"
          onAction={() => (window.location.href = "/documents")}
          icon={<ListOrdered className="w-6 h-6 text-outline" />}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-start w-full">
          {/* ========================================================= */}
          {/* LEFT PANEL: REQUIREMENT LIST (~58% / 7 cols)              */}
          {/* ========================================================= */}
          <div className="lg:col-span-6 xl:col-span-7 flex flex-col bg-surface-container-lowest rounded-xl border border-outline-variant/60 shadow-xs overflow-hidden">
            {/* Table Header */}
            <div className="grid grid-cols-12 items-center px-4 py-2.5 bg-surface-container-low/70 border-b border-outline-variant/50 text-[10px] uppercase font-semibold text-outline tracking-wider select-none">
              <div className="col-span-4">Requirement ID</div>
              <div className="col-span-6">Statement Preview</div>
              <div className="col-span-2 text-right">Class</div>
            </div>

            {/* Rows List */}
            <div className="divide-y divide-outline-variant/30 max-h-[calc(100vh-230px)] overflow-y-auto">
              {filteredRequirements.map((req) => {
                const isSelected = selectedReqId === req.id;
                return (
                  <article
                    key={req.id}
                    onClick={() => setSelectedReqId(req.id)}
                    className={`grid grid-cols-12 p-3.5 transition-colors cursor-pointer text-xs relative ${
                      isSelected
                        ? "bg-surface-container-high/50 before:absolute before:left-0 before:top-0 before:bottom-0 before:w-1 before:bg-secondary"
                        : "hover:bg-surface-container-low/50"
                    }`}
                  >
                    {/* ID & Section */}
                    <div className="col-span-4 flex flex-col items-start gap-1 pr-2">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`font-mono font-bold tracking-tight ${
                            isSelected ? "text-secondary" : "text-on-surface"
                          }`}
                        >
                          {req.req_key}
                        </span>
                      </div>
                      <span className="text-[10px] text-outline truncate max-w-[130px]">
                        {req.section || req.source_layer}
                      </span>
                    </div>

                    {/* Statement Preview */}
                    <div className="col-span-6 pr-2">
                      <p className="line-clamp-2 text-on-surface leading-relaxed text-xs">
                        {req.text}
                      </p>
                    </div>

                    {/* Classification */}
                    <div className="col-span-2 flex flex-col items-end justify-center">
                      <span
                        className={`text-[10px] px-1.5 py-0.5 rounded font-medium border ${
                          req.classification_label === "Functional"
                            ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {req.classification_label === "Functional" ? "Func" : "Non-Func"}
                      </span>
                    </div>
                  </article>
                );
              })}
            </div>
          </div>

          {/* ========================================================= */}
          {/* RIGHT PANEL: DENSE INSPECTION WORKSPACE (~42% / 5 cols)    */}
          {/* ========================================================= */}
          <div className="lg:col-span-6 xl:col-span-5 flex flex-col bg-surface-container-lowest rounded-xl border border-outline-variant/60 shadow-xs p-4 gap-4 sticky top-16 max-h-[calc(100vh-140px)] overflow-y-auto">
            {loadingDetail ? (
              <LoadingState message="Loading requirement details..." className="py-12" />
            ) : !reqDetail ? (
              <EmptyState
                title="Select a requirement"
                description="Click any requirement from the list to view its quality score, waterfall trace, and SHAP token attributions."
                icon={<Layers className="w-5 h-5 text-outline" />}
              />
            ) : (
              <>
                {/* 1. Header & Quick Actions */}
                <div className="flex items-start justify-between gap-3 pb-3 border-b border-outline-variant/40">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-bold font-mono text-on-surface">
                        {reqDetail.req_key}
                      </h2>
                      <button
                        onClick={copyReqId}
                        className="p-1 text-outline hover:text-on-surface rounded hover:bg-surface-container transition-colors"
                        title="Copy Requirement ID"
                      >
                        {copiedId ? (
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>

                    <div className="flex items-center gap-1.5 mt-1">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded font-medium border ${
                          reqDetail.classification_label === "Functional"
                            ? "bg-indigo-50 text-indigo-700 border-indigo-200"
                            : "bg-amber-50 text-amber-700 border-amber-200"
                        }`}
                      >
                        {reqDetail.classification_label} (
                        {reqDetail.classification_prob
                          ? `${(reqDetail.classification_prob * 100).toFixed(1)}%`
                          : "—"}
                        )
                      </span>
                      <span className="text-[10px] px-2 py-0.5 rounded bg-surface-container text-outline font-mono">
                        {reqDetail.source_layer}
                      </span>
                    </div>
                  </div>

                  {/* Quality Score Gauge Card */}
                  <div
                    className={`flex items-center gap-2.5 px-3 py-2 rounded-xl border ${getScoreColor(
                      reqDetail.quality_score
                    )}`}
                  >
                    <div className="text-center">
                      <span className="text-xl font-black font-mono leading-none block">
                        {reqDetail.quality_score !== undefined
                          ? Math.round(reqDetail.quality_score)
                          : "—"}
                      </span>
                      <span className="text-[9px] uppercase tracking-wider font-semibold opacity-70">
                        Score /100
                      </span>
                    </div>
                  </div>
                </div>

                {/* 2. Requirement Statement & Highlighted Spans */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                      Requirement Statement
                    </span>
                    {reqDetail.issues.length > 0 && (
                      <span className="text-[10px] text-amber-700 font-medium">
                        {reqDetail.issues.length} potential issue
                        {reqDetail.issues.length > 1 ? "s" : ""}
                      </span>
                    )}
                  </div>

                  <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/50 text-xs leading-relaxed text-on-surface">
                    {renderHighlightedStatement(reqDetail.text, reqDetail.issues)}
                  </div>
                </div>

                {/* 2b. AI Assistance (Phase 14: Tier 2 Rewrite & Gherkin) */}
                <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-secondary" />
                      <span className="text-xs font-semibold text-on-surface">AI Assistance (Tier 2)</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleSuggestRewrite}
                        disabled={loadingRewrite}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-secondary/10 hover:bg-secondary/20 text-secondary text-[11px] font-medium transition-colors border border-secondary/30 disabled:opacity-50"
                      >
                        <Sparkles className="w-3 h-3" />
                        <span>{loadingRewrite ? "Generating..." : "Suggest Rewrite"}</span>
                      </button>

                      <button
                        type="button"
                        onClick={handleGenerateGherkin}
                        disabled={loadingGherkin}
                        className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-indigo-50 hover:bg-indigo-100 text-indigo-800 text-[11px] font-medium transition-colors border border-indigo-200 disabled:opacity-50"
                      >
                        <ListOrdered className="w-3 h-3" />
                        <span>{loadingGherkin ? "Generating..." : "Generate Gherkin"}</span>
                      </button>
                    </div>
                  </div>

                  {/* Active AI Result Panel */}
                  {activeAiTab === "rewrite" && rewriteResult && (
                    <div className="p-3 rounded-xl border border-secondary/40 bg-secondary/5 flex flex-col gap-2.5 text-xs animate-in fade-in">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <Sparkles className="w-3.5 h-3.5 text-secondary" />
                          <span className="font-semibold text-on-surface">AI Rewrite Proposal</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {rewriteResult.cached && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-outline border border-outline-variant/50">
                              Cached
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => setActiveAiTab("none")}
                            className="text-outline hover:text-on-surface"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {!rewriteResult.enabled ? (
                        <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-800 text-[11px]">
                          {rewriteResult.rationale || "LLM service is currently disabled."}
                        </div>
                      ) : rewriteResult.error ? (
                        <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-800 text-[11px]">
                          {rewriteResult.error}
                        </div>
                      ) : (
                        <>
                          <div className="p-2 rounded bg-surface-container-lowest border border-outline-variant/40 flex flex-col gap-1">
                            <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">Suggested Statement</span>
                            <p className="text-xs font-medium text-emerald-800 font-sans leading-relaxed">
                              {rewriteResult.suggested_text}
                            </p>
                          </div>

                          {rewriteResult.rationale && (
                            <div className="text-[11px] text-on-surface-variant leading-relaxed">
                              <strong className="text-on-surface">Rationale: </strong>
                              {rewriteResult.rationale}
                            </div>
                          )}

                          {rewriteResult.changes_made && rewriteResult.changes_made.length > 0 && (
                            <div className="flex flex-col gap-1">
                              <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">Key Changes</span>
                              <ul className="list-disc list-inside text-[11px] text-on-surface-variant space-y-0.5">
                                {rewriteResult.changes_made.map((ch, idx) => (
                                  <li key={idx}>{ch}</li>
                                ))}
                              </ul>
                            </div>
                          )}

                          {/* Action button to apply suggestion */}
                          <div className="flex items-center justify-end gap-2 pt-1 border-t border-secondary/20">
                            <button
                              type="button"
                              onClick={() => {
                                if (rewriteResult.suggested_text && reqDetail.issues.length > 0) {
                                  setEditingIssueId(reqDetail.issues[0].id);
                                  setEditText(rewriteResult.suggested_text);
                                }
                              }}
                              className="inline-flex items-center gap-1 px-3 py-1 rounded bg-secondary text-white hover:bg-secondary/90 text-xs font-medium transition-colors"
                            >
                              <Check className="w-3.5 h-3.5" />
                              <span>Use This Rewrite</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}

                  {activeAiTab === "gherkin" && gherkinResult && (
                    <div className="p-3 rounded-xl border border-indigo-200 bg-indigo-50/40 flex flex-col gap-2.5 text-xs animate-in fade-in">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          <ListOrdered className="w-3.5 h-3.5 text-indigo-700" />
                          <span className="font-semibold text-on-surface">Gherkin Test Scenarios</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                          {gherkinResult.source === "ears_rule" && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 border border-emerald-300">
                              EARS Rule-Based
                            </span>
                          )}
                          {gherkinResult.source === "llm" && (
                            <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-800 border border-indigo-300">
                              LLM Generated
                            </span>
                          )}
                          {gherkinResult.ears_pattern && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/40">
                              {gherkinResult.ears_pattern}
                            </span>
                          )}
                          {gherkinResult.cached && (
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-outline border border-outline-variant/50">
                              Cached
                            </span>
                          )}
                          <button
                            type="button"
                            onClick={() => setActiveAiTab("none")}
                            className="text-outline hover:text-on-surface"
                          >
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {!gherkinResult.enabled ? (
                        <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-amber-800 text-[11px]">
                          {gherkinResult.error || "LLM service is currently disabled."}
                        </div>
                      ) : gherkinResult.error ? (
                        <div className="p-2.5 rounded bg-rose-50 border border-rose-200 text-rose-800 text-[11px]">
                          {gherkinResult.error}
                        </div>
                      ) : (
                        <>
                          <pre className="p-2.5 rounded bg-surface-container-lowest border border-outline-variant/40 font-mono text-[11px] leading-relaxed text-on-surface overflow-x-auto whitespace-pre-wrap">
                            {gherkinResult.gherkin_scenarios}
                          </pre>
                          <div className="flex items-center justify-end gap-2 pt-1 border-t border-indigo-200">
                            <button
                              type="button"
                              onClick={() => {
                                if (gherkinResult.gherkin_scenarios) {
                                  navigator.clipboard.writeText(gherkinResult.gherkin_scenarios);
                                  setCopiedGherkin(true);
                                  setTimeout(() => setCopiedGherkin(false), 2000);
                                }
                              }}
                              className="inline-flex items-center gap-1 px-3 py-1 rounded bg-indigo-600 text-white hover:bg-indigo-700 text-xs font-medium transition-colors"
                            >
                              <Copy className="w-3.5 h-3.5" />
                              <span>{copiedGherkin ? "Copied!" : "Copy Scenarios"}</span>
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>

                {/* 3. SHAP Word Feature Attribution Chart */}
                {shapTokens.length > 0 && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Sparkles className="w-3.5 h-3.5 text-secondary" />
                        <span className="text-xs font-semibold text-on-surface">
                          Classification Attribution (SHAP)
                        </span>
                      </div>
                      <span className="text-[10px] text-outline font-mono">LinearExplainer</span>
                    </div>

                    {/* Word Tokens Strip */}
                    <div className="flex flex-wrap gap-1 p-2 rounded-lg bg-surface-container-low border border-outline-variant/40 text-[11px] font-mono">
                      {shapTokens.map((st, i) => (
                        <span
                          key={i}
                          className={`px-1.5 py-0.5 rounded ${
                            st.shap_value >= 0
                              ? "bg-indigo-50 text-indigo-900 border border-indigo-200"
                              : "bg-rose-50 text-rose-900 border border-rose-200"
                          }`}
                        >
                          {st.token}{" "}
                          <strong
                            className={st.shap_value >= 0 ? "text-indigo-600" : "text-rose-600"}
                          >
                            {st.shap_value >= 0 ? `+${st.shap_value.toFixed(2)}` : st.shap_value.toFixed(2)}
                          </strong>
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* 4. Score Deductions (Waterfall) */}
                {reqDetail.waterfall && reqDetail.waterfall.length > 0 && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <BarChart3 className="w-3.5 h-3.5 text-secondary" />
                        <span className="text-xs font-semibold text-on-surface">
                          Waterfall Penalty Deductions
                        </span>
                      </div>
                      <span className="text-[10px] text-outline font-mono">Base: 100 pts</span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-1.5 font-mono text-[11px]">
                      {reqDetail.waterfall.map((step, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <span
                            className={
                              step.deduction < 0 ? "text-rose-700" : "text-on-surface-variant"
                            }
                          >
                            {step.step_name}: {step.explanation}
                          </span>
                          <span
                            className={`font-semibold ${
                              step.deduction < 0 ? "text-rose-600" : "text-on-surface"
                            }`}
                          >
                            {step.deduction < 0
                              ? `${step.deduction.toFixed(1)}`
                              : `${step.current_score.toFixed(1)}`}
                          </span>
                        </div>
                      ))}
                      <div className="pt-1 mt-1 border-t border-outline-variant/50 flex items-center justify-between font-bold text-on-surface">
                        <span>Final Calculated Score</span>
                        <span>{reqDetail.quality_score?.toFixed(1) ?? "—"} / 100</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* 5. 6 Sub-Scores Grid */}
                {reqDetail.sub_scores && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                    <span className="text-xs font-semibold text-on-surface">
                      Sub-Score Breakdown
                    </span>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-2">
                      {Object.entries(reqDetail.sub_scores).map(([key, val]) => (
                        <div key={key} className="flex flex-col gap-1">
                          <div className="flex justify-between text-[11px]">
                            <span className="capitalize text-outline">{key}</span>
                            <span className="font-mono font-medium text-on-surface">
                              {Math.round(val)}%
                            </span>
                          </div>
                          <div className="w-full bg-outline-variant/30 h-1.5 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${getScoreBarColor(val)}`}
                              style={{ width: `${val}%` }}
                            ></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 5b. EARS Syntax & ISO 29148 Standards Checks */}
                {reqDetail.ears_result && (
                  <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-blue-600" />
                        <span className="text-xs font-semibold text-on-surface">
                          EARS Syntax & ISO 29148
                        </span>
                      </div>
                      <span
                        className={`text-[10px] font-mono px-2 py-0.5 rounded font-medium border ${
                          reqDetail.ears_result.is_valid_ears
                            ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                            : "bg-amber-50 text-amber-800 border-amber-200"
                        }`}
                      >
                        {reqDetail.ears_result.pattern.replace("_", " ").toUpperCase()}
                      </span>
                    </div>

                    <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2 text-xs">
                      {reqDetail.ears_result.matched_template && (
                        <div className="flex items-start gap-1.5">
                          <span className="text-[11px] text-outline font-medium flex-shrink-0">Template:</span>
                          <span className="text-[11px] font-mono text-on-surface bg-surface-container px-1.5 py-0.5 rounded">
                            {reqDetail.ears_result.matched_template}
                          </span>
                        </div>
                      )}
                      <p className="text-[11px] text-on-surface-variant leading-relaxed">
                        {reqDetail.ears_result.explanation}
                      </p>
                      {reqDetail.ears_result.suggestion && (
                        <div className="p-2 rounded bg-blue-50/60 border border-blue-200 text-blue-900 text-[11px] flex items-start gap-1.5">
                          <span className="font-semibold flex-shrink-0">Tip:</span>
                          <span>{reqDetail.ears_result.suggestion}</span>
                        </div>
                      )}

                      {/* 7 ISO Checks Pills */}
                      {reqDetail.iso_checks && reqDetail.iso_checks.length > 0 && (
                        <div className="flex flex-col gap-1 pt-1.5 border-t border-outline-variant/40">
                          <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                            Selected Machine-Checkable ISO 29148 Checks
                          </span>
                          <div className="grid grid-cols-2 gap-1.5">
                            {reqDetail.iso_checks.map((chk) => (
                              <div
                                key={chk.check_id}
                                title={`${chk.characteristic}: ${chk.explanation}`}
                                className={`flex items-center justify-between p-1.5 rounded border text-[10px] ${
                                  chk.status === "passed"
                                    ? "bg-emerald-50/60 border-emerald-200 text-emerald-800"
                                    : chk.status === "warning"
                                    ? "bg-amber-50/60 border-amber-200 text-amber-800"
                                    : "bg-rose-50/60 border-rose-200 text-rose-800"
                                }`}
                              >
                                <span className="font-medium truncate">{chk.characteristic}</span>
                                <span className="font-mono font-bold uppercase text-[9px] ml-1">
                                  {chk.status === "passed" ? "✓" : chk.status === "warning" ? "!" : "✕"}
                                </span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* 6. Detected Issues & Human-in-the-Loop Review Actions */}
                <div className="flex flex-col gap-2 pt-2 border-t border-outline-variant/30">
                  <div className="flex items-center justify-between">

                    <span className="text-xs font-semibold text-on-surface">
                      Findings & Remediation
                    </span>
                    <span className="text-[10px] font-mono text-outline">
                      {reqDetail.issues.length} detected
                    </span>
                  </div>

                  {reqDetail.issues.length === 0 ? (
                    <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs flex items-center gap-2">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
                      <span>No potential quality defects detected in this requirement.</span>
                    </div>
                  ) : (
                    <div className="flex flex-col gap-3">
                      {reqDetail.issues.map((issue) => {
                        const exp = issue.explanation as any;
                        const isEditing = editingIssueId === issue.id;

                        return (
                          <div
                            key={issue.id}
                            className="p-3 rounded-xl border border-outline-variant/60 bg-surface-container-low/40 flex flex-col gap-2.5 text-xs"
                          >
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-1.5">
                                <span
                                  className={`w-2 h-2 rounded-full ${
                                    issue.severity === "error"
                                      ? "bg-rose-600"
                                      : issue.severity === "warning"
                                      ? "bg-amber-600"
                                      : "bg-blue-600"
                                  }`}
                                ></span>
                                <span className="font-semibold text-on-surface">
                                  {issue.type}
                                </span>
                              </div>
                              <span
                                className={`text-[10px] px-1.5 py-0.5 rounded font-mono font-medium uppercase ${
                                  issue.status === "accepted"
                                    ? "bg-emerald-100 text-emerald-800 border border-emerald-200"
                                    : issue.status === "rejected"
                                    ? "bg-slate-200 text-slate-700"
                                    : issue.status === "edited"
                                    ? "bg-indigo-100 text-indigo-800 border border-indigo-200"
                                    : "bg-amber-100 text-amber-800 border border-amber-200"
                                }`}
                              >
                                {issue.status}
                              </span>
                            </div>

                            {/* Human Explanation */}
                            <p className="text-on-surface-variant leading-relaxed">
                              {exp?.human_explanation || "Defect identified by automated rule."}
                            </p>

                            {/* Suggestion */}
                            {exp?.suggestion && (
                              <div className="p-2 rounded bg-surface-container-lowest border border-outline-variant/40 flex flex-col gap-0.5">
                                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                                  Suggestion
                                </span>
                                <span className="text-secondary font-mono text-[11px]">
                                  {exp.suggestion}
                                </span>
                              </div>
                            )}

                            {/* Inline Edit Area */}
                            {isEditing ? (
                              <div className="flex flex-col gap-2 pt-1">
                                <textarea
                                  value={editText}
                                  onChange={(e) => setEditText(e.target.value)}
                                  rows={3}
                                  className="w-full p-2 text-xs rounded-lg border border-secondary bg-surface-container-lowest text-on-surface focus:outline-none"
                                />
                                <div className="flex items-center gap-2 justify-end">
                                  <button
                                    onClick={() => setEditingIssueId(null)}
                                    className="px-2.5 py-1 text-xs rounded border border-outline-variant/60 text-outline hover:text-on-surface"
                                  >
                                    Cancel
                                  </button>
                                  <button
                                    onClick={() => handleReview(issue.id, "edit")}
                                    className="px-3 py-1 text-xs rounded bg-primary text-on-primary hover:bg-primary-container font-medium"
                                  >
                                    Save & Update Text
                                  </button>
                                </div>
                              </div>
                            ) : (
                              /* Review Buttons */
                              <div className="flex items-center gap-2 pt-1 border-t border-outline-variant/30">
                                <button
                                  type="button"
                                  onClick={() => handleReview(issue.id, "accept")}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300 border border-outline-variant/50 text-[11px] font-medium transition-colors"
                                >
                                  <Check className="w-3 h-3 text-emerald-600" />
                                  <span>Accept</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => handleReview(issue.id, "reject")}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container hover:bg-rose-50 hover:text-rose-800 hover:border-rose-300 border border-outline-variant/50 text-[11px] font-medium transition-colors"
                                >
                                  <X className="w-3 h-3 text-rose-600" />
                                  <span>Reject</span>
                                </button>

                                <button
                                  type="button"
                                  onClick={() => {
                                    setEditingIssueId(issue.id);
                                    setEditText(reqDetail.text);
                                  }}
                                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-surface-container hover:bg-indigo-50 hover:text-indigo-800 hover:border-indigo-300 border border-outline-variant/50 text-[11px] font-medium transition-colors ml-auto"
                                >
                                  <Edit3 className="w-3 h-3 text-indigo-600" />
                                  <span>Edit Statement</span>
                                </button>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RequirementsPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading Requirement Viewer..." className="py-20" />}>
      <RequirementViewerContent />
    </Suspense>
  );
}
