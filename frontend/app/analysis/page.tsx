"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  Check,
  X,
  Edit3,
  Search,
  Filter,
  Layers,
  ChevronDown,
  Copy,
  ArrowRight,
  ExternalLink,
  GitCompare,
  BookOpen,
  Sparkles,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  Issue,
  DuplicatePair,
  ContradictionItem,
  Requirement,
  ClusterGroup,
} from "@/types";

function AnalysisPageContent() {
  const searchParams = useSearchParams();
  const initialDocParam = searchParams.get("doc");

  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(
    initialDocParam ? parseInt(initialDocParam, 10) : null
  );

  const [issues, setIssues] = useState<Issue[]>([]);
  const [duplicatePairs, setDuplicatePairs] = useState<DuplicatePair[]>([]);
  const [contradictions, setContradictions] = useState<ContradictionItem[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [clusters, setClusters] = useState<ClusterGroup[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Tabs: all, ambiguity, duplicates, contradictions, standards, clusters, readability
  const [activeTab, setActiveTab] = useState<"all" | "ambiguity" | "duplicates" | "contradictions" | "standards" | "clusters" | "readability">("all");

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [severityFilter, setSeverityFilter] = useState<"all" | "error" | "warning" | "info">("all");
  const [statusFilter, setStatusFilter] = useState<"all" | "ai_flagged" | "accepted" | "rejected" | "edited">("all");

  // Inline editing state for an issue
  const [editingIssueId, setEditingIssueId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const [actionNotice, setActionNotice] = useState<{ type: "success" | "error"; message: string } | null>(null);

  // On-demand Captum token attribution state
  const [attributionsMap, setAttributionsMap] = useState<Record<number, { token: string; attribution: number }[]>>({});
  const [explainingIssueId, setExplainingIssueId] = useState<number | null>(null);

  // 1. Fetch available documents
  useEffect(() => {
    async function loadDocs() {
      try {
        setLoading(true);
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length > 0) {
          if (!selectedDocId || !docs.some((d) => d.id === selectedDocId)) {
            const analyzed = docs.find((d) => d.status === "analyzed");
            setSelectedDocId(analyzed ? analyzed.id : docs[0].id);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load documents index");
      } finally {
        setLoading(false);
      }
    }
    loadDocs();
  }, []);

  // 2. Fetch issues, duplicates, contradictions, and requirements for the selected document
  const fetchDocumentAnalysisData = async (docId: number) => {
    try {
      setLoading(true);
      setError(null);

      const [docIssues, dupesRes, contraRes, reqs, clustersRes] = await Promise.all([
        api.getDocumentIssues(docId).catch(() => []),
        api.getDocumentDuplicates(docId).catch(() => ({ duplicates: [] })),
        api.getDocumentContradictions(docId).catch(() => ({ contradictions: [] })),
        api.getDocumentRequirements(docId).catch(() => []),
        api.getDocumentClusters(docId).catch(() => ({ clusters: [] })),
      ]);

      setIssues(docIssues);
      setDuplicatePairs(dupesRes.duplicates || []);
      setContradictions(contraRes.contradictions || []);
      setRequirements(reqs);
      setClusters(clustersRes.clusters || []);
    } catch (err: any) {
      setError(err.message || "Failed to fetch document analysis findings");
    } finally {
      setLoading(false);
    }
  };

  const handleExplain = async (issueId: number) => {
    try {
      setExplainingIssueId(issueId);
      const res = await api.explainContradiction(issueId);
      setAttributionsMap((prev) => ({ ...prev, [issueId]: res.tokens }));
    } catch (err: any) {
      console.error("Failed to fetch contradiction attribution:", err);
    } finally {
      setExplainingIssueId(null);
    }
  };

  useEffect(() => {
    if (selectedDocId) {
      fetchDocumentAnalysisData(selectedDocId);
    }
  }, [selectedDocId]);

  // Handle Review Action (Accept, Reject, Edit)
  const handleReview = async (issueId: number, action: "accept" | "reject" | "edit") => {
    try {
      setActionNotice(null);
      await api.reviewIssue(issueId, {
        action,
        edited_text: action === "edit" ? editText : undefined,
        note: action === "edit" ? "Direct remediation applied during analysis review." : undefined,
      });

      setActionNotice({
        type: "success",
        message: `Issue finding marked as ${action.toUpperCase()} successfully.`,
      });

      // Reload issues and requirements
      if (selectedDocId) {
        await fetchDocumentAnalysisData(selectedDocId);
      }
      setEditingIssueId(null);
    } catch (err: any) {
      setActionNotice({
        type: "error",
        message: `Failed to record review action: ${err.message || "Unknown error"}`,
      });
    }
  };

  // Grouped counts for tab badges
  const ambiguityIssues = useMemo(() => {
    return issues.filter((i) => i.module === "ambiguity" || i.type.includes("WEAK") || i.type.includes("AMB"));
  }, [issues]);

  const readabilityIssues = useMemo(() => {
    return issues.filter((i) => i.module === "readability" || i.type.includes("READABILITY"));
  }, [issues]);

  const standardsIssues = useMemo(() => {
    return issues.filter((i) => i.module === "standards" || i.type.startsWith("ISO_"));
  }, [issues]);

  // Filter issues based on active tab, search, severity, and status
  const filteredIssues = useMemo(() => {
    return issues.filter((i) => {
      // Tab filter
      if (activeTab === "ambiguity") {
        if (i.module !== "ambiguity" && !i.type.includes("WEAK") && !i.type.includes("AMB")) return false;
      } else if (activeTab === "readability") {
        if (i.module !== "readability" && !i.type.includes("READABILITY")) return false;
      } else if (activeTab === "standards") {
        if (i.module !== "standards" && !i.type.startsWith("ISO_")) return false;
      }

      // Severity filter
      if (severityFilter !== "all" && i.severity !== severityFilter) return false;

      // Status filter
      if (statusFilter !== "all" && i.status !== statusFilter) return false;

      // Search query
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const exp = i.explanation as any;
        const matchesKey = i.req_key ? i.req_key.toLowerCase().includes(q) : false;
        const matchesType = i.type.toLowerCase().includes(q);
        const matchesExp = exp?.human_explanation?.toLowerCase().includes(q) || false;
        if (!matchesKey && !matchesType && !matchesExp) return false;
      }

      return true;
    });
  }, [issues, activeTab, severityFilter, statusFilter, searchQuery]);

  // Requirement text lookup map
  const reqTextMap = useMemo(() => {
    const map = new Map<string, string>();
    requirements.forEach((r) => map.set(r.req_key, r.text));
    return map;
  }, [requirements]);

  const getSeverityBadge = (sev: string) => {
    if (sev === "error") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-rose-100 text-rose-800 border border-rose-200">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
          CRITICAL
        </span>
      );
    }
    if (sev === "warning") {
      return (
        <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-amber-100 text-amber-800 border border-amber-200">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-600"></span>
          WARNING
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-blue-100 text-blue-800 border border-blue-200">
        <span className="w-1.5 h-1.5 rounded-full bg-blue-600"></span>
        INFO
      </span>
    );
  };

  const getStatusBadge = (st: string) => {
    switch (st) {
      case "accepted":
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-medium bg-emerald-50 text-emerald-800 border border-emerald-200">
            ACCEPTED
          </span>
        );
      case "rejected":
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-medium bg-slate-100 text-slate-700 border border-slate-200">
            REJECTED
          </span>
        );
      case "edited":
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-medium bg-indigo-50 text-indigo-800 border border-indigo-200">
            EDITED
          </span>
        );
      default:
        return (
          <span className="text-[10px] font-mono px-2 py-0.5 rounded font-medium bg-amber-50 text-amber-800 border border-amber-200">
            UNREVIEWED
          </span>
        );
    }
  };

  return (
    <div className="flex flex-col gap-5 max-w-7xl mx-auto w-full">
      {/* Top Header & Document Context Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            Analysis & Issue Review
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            ISO/IEC/IEEE 29148 Automated Defect Inspection • Human-in-the-loop Remediation
          </p>
        </div>

        {/* Document Selector & Navigation */}
        <div className="flex items-center gap-2 flex-wrap">
          {documents.length > 0 && (
            <div className="relative">
              <select
                value={selectedDocId || ""}
                onChange={(e) => setSelectedDocId(parseInt(e.target.value, 10))}
                className="h-8 pl-3 pr-8 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-xs font-semibold text-on-surface focus:outline-none focus:border-secondary transition-colors cursor-pointer appearance-none shadow-xs"
              >
                {documents.map((doc) => (
                  <option key={doc.id} value={doc.id}>
                    {doc.filename} ({doc.status})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-outline absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          )}

          {selectedDocId && (
            <Link
              href={`/requirements?doc=${selectedDocId}`}
              className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-surface-container-low border border-outline-variant/60 hover:bg-surface-container text-on-surface text-xs font-medium transition-colors shadow-xs"
            >
              <Layers className="w-3.5 h-3.5 text-outline" />
              <span>Requirement Viewer</span>
            </Link>
          )}
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div
          className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
            actionNotice.type === "success"
              ? "bg-emerald-50 text-emerald-900 border-emerald-200"
              : "bg-rose-50 text-rose-900 border-rose-200"
          }`}
        >
          <div className="flex items-center gap-2">
            {actionNotice.type === "success" ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span>{actionNotice.message}</span>
          </div>
          <button
            onClick={() => setActionNotice(null)}
            className="text-xs opacity-60 hover:opacity-100 font-bold"
          >
            ✕
          </button>
        </div>
      )}

      {/* Verification Workspace Category Tabs */}
      <div className="flex items-center gap-1.5 p-1 bg-surface-container-lowest rounded-xl border border-outline-variant/50 shadow-xs overflow-x-auto select-none">
        <button
          onClick={() => setActiveTab("all")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "all"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <AlertCircle className="w-3.5 h-3.5" />
          <span>All Findings</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-surface-container-high text-on-surface">
            {issues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("ambiguity")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "ambiguity"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
          <span>Ambiguity & Weak Terms</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-amber-100 text-amber-800">
            {ambiguityIssues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("duplicates")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "duplicates"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <GitCompare className="w-3.5 h-3.5 text-secondary" />
          <span>Semantic Duplicates</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-secondary-fixed text-on-secondary-fixed">
            {duplicatePairs.length} pairs
          </span>
        </button>

        <button
          onClick={() => setActiveTab("contradictions")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "contradictions"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <AlertTriangle className="w-3.5 h-3.5 text-rose-600" />
          <span>Contradictions</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-rose-100 text-rose-800 border border-rose-200">
            {contradictions.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("standards")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "standards"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-blue-600" />
          <span>ISO 29148 Checks</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-blue-100 text-blue-800 border border-blue-200">
            {standardsIssues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("readability")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "readability"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <BookOpen className="w-3.5 h-3.5 text-outline" />
          <span>Readability & Voice</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-surface-container-high text-on-surface">
            {readabilityIssues.length}
          </span>
        </button>

        <button
          onClick={() => setActiveTab("clusters")}
          className={`h-8 px-3.5 rounded-lg flex items-center gap-2 text-xs font-medium transition-colors ${
            activeTab === "clusters"
              ? "bg-surface-container text-on-surface font-semibold shadow-xs"
              : "text-on-surface-variant hover:bg-surface-container-low"
          }`}
        >
          <Layers className="w-3.5 h-3.5 text-indigo-600" />
          <span>Thematic Clusters</span>
          <span className="font-mono text-[10px] px-1.5 py-0.2 rounded bg-indigo-100 text-indigo-800 border border-indigo-200">
            {clusters.length}
          </span>
        </button>
      </div>

      {/* Filter Toolbar (for issue tabs) */}
      {activeTab !== "duplicates" && activeTab !== "contradictions" && activeTab !== "clusters" && (
        <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/50 shadow-xs text-xs">
          <div className="flex items-center gap-2 flex-wrap">
            {/* Search */}
            <div className="relative flex items-center w-56 h-7 px-2 rounded-lg bg-surface-container-low border border-outline-variant/60 focus-within:border-secondary transition-all">
              <Search className="w-3 h-3 text-outline mr-1.5 flex-shrink-0" />
              <input
                type="text"
                placeholder="Filter findings..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none outline-none text-xs text-on-surface placeholder:text-outline"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery("")} className="text-outline hover:text-on-surface">
                  ×
                </button>
              )}
            </div>

            {/* Severity Filter */}
            <select
              value={severityFilter}
              onChange={(e: any) => setSeverityFilter(e.target.value)}
              className="h-7 px-2 rounded bg-surface-container-low border border-outline-variant/50 text-[11px] text-on-surface"
            >
              <option value="all">Severity: All</option>
              <option value="error">Critical (Error)</option>
              <option value="warning">Warning</option>
              <option value="info">Info</option>
            </select>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e: any) => setStatusFilter(e.target.value)}
              className="h-7 px-2 rounded bg-surface-container-low border border-outline-variant/50 text-[11px] text-on-surface"
            >
              <option value="all">Status: All</option>
              <option value="ai_flagged">Unreviewed Only</option>
              <option value="accepted">Accepted</option>
              <option value="rejected">Rejected</option>
              <option value="edited">Edited</option>
            </select>
          </div>

          <span className="text-outline text-[11px] font-mono">
            Showing {filteredIssues.length} of {issues.length} findings
          </span>
        </div>
      )}

      {/* Main Content Area */}
      {loading ? (
        <LoadingState message="Loading analysis findings..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
      ) : activeTab === "duplicates" ? (
        /* ========================================================= */
        /* TAB 2: SEMANTIC DUPLICATES (SIDE-BY-SIDE VIEW)            */
        /* ========================================================= */
        duplicatePairs.length === 0 ? (
          <EmptyState
            title="No semantic duplicates detected"
            description="All requirements in this specification meet semantic distinction standards (cosine similarity < 80%)."
            icon={<GitCompare className="w-6 h-6 text-outline" />}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="p-3 bg-secondary-fixed/40 border border-secondary/20 rounded-xl text-xs text-on-surface flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-secondary" />
                <span>
                  Detected <strong>{duplicatePairs.length} candidate duplicate pairs</strong> exceeding 80% embedding cosine similarity with <code>all-MiniLM-L6-v2</code>.
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              {duplicatePairs.map((pair, idx) => (
                <div
                  key={idx}
                  className="p-4 rounded-xl border border-outline-variant/60 bg-surface-container-lowest shadow-xs flex flex-col gap-3"
                >
                  {/* Pair Header */}
                  <div className="flex items-center justify-between pb-2 border-b border-outline-variant/40">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold font-mono text-on-surface">
                        Duplicate Pair #{idx + 1}
                      </span>
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-indigo-50 text-indigo-800 border border-indigo-200">
                        {Math.round(pair.similarity_score * 100)}% Cosine Similarity
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <Link
                        href={`/requirements?doc=${selectedDocId}&req=${pair.requirement_id_1}`}
                        className="text-[11px] text-secondary hover:underline flex items-center gap-1 font-mono"
                      >
                        <span>View {pair.req_key_1}</span>
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>

                  {/* Side-by-Side Comparison Box */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Requirement 1 */}
                    <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/40 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-secondary">
                          {pair.req_key_1}
                        </span>
                        <span className="text-[10px] text-outline font-mono">Original</span>
                      </div>
                      <p className="text-xs text-on-surface leading-relaxed">
                        {pair.text_1}
                      </p>
                    </div>

                    {/* Requirement 2 */}
                    <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/40 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono font-bold text-secondary">
                          {pair.req_key_2}
                        </span>
                        <span className="text-[10px] text-outline font-mono">Duplicate Candidate</span>
                      </div>
                      <p className="text-xs text-on-surface leading-relaxed">
                        {pair.text_2}
                      </p>
                    </div>
                  </div>

                  {/* Aligned Phrases Attribution */}
                  {pair.aligned_phrases && pair.aligned_phrases.length > 0 && (
                    <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/30 flex flex-col gap-1.5 text-xs">
                      <span className="text-[10px] uppercase font-semibold text-outline tracking-wider">
                        Key Aligned Semantic Phrases
                      </span>
                      <div className="flex flex-col gap-1">
                        {pair.aligned_phrases.map((ap, pIdx) => (
                          <div key={pIdx} className="flex items-center justify-between text-[11px] font-mono">
                            <span className="text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant/30">
                              "{ap.phrase_1.text}"
                            </span>
                            <span className="text-outline text-[10px]">⟷</span>
                            <span className="text-on-surface bg-surface-container-lowest px-1.5 py-0.5 rounded border border-outline-variant/30">
                              "{ap.phrase_2.text}"
                            </span>
                            <span className="text-secondary font-semibold">
                              {Math.round(ap.similarity * 100)}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      ) : activeTab === "contradictions" ? (
        /* ========================================================= */
        /* TAB 3: CONTRADICTIONS (SIDE-BY-SIDE CONFLICT VIEW)        */
        /* ========================================================= */
        contradictions.length === 0 ? (
          <EmptyState
            title="No potential contradictions detected"
            description="All quantitative constraints and semantic assertions are mutually compatible."
            icon={<AlertTriangle className="w-6 h-6 text-outline" />}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-xs text-on-surface flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-rose-600" />
                <span>
                  Detected <strong>{contradictions.length} potential contradiction{contradictions.length > 1 ? "s" : ""}</strong> (
                  {contradictions.filter((c) => c.mechanism === "numeric").length} numeric constraint conflicts,{" "}
                  {contradictions.filter((c) => c.mechanism === "semantic").length} semantic contradictions). Every detection requires human engineer review.
                </span>
              </div>
            </div>

            <div className="flex flex-col gap-4">
              {contradictions.map((c, idx) => (
                <div
                  key={c.finding_id || idx}
                  className="p-4 rounded-xl border border-rose-200 bg-surface-container-lowest shadow-xs flex flex-col gap-3"
                >
                  {/* Contradiction Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-outline-variant/40">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded font-mono font-medium bg-rose-100 text-rose-800 border border-rose-200">
                        <span className="w-1.5 h-1.5 rounded-full bg-rose-600"></span>
                        POTENTIAL CONTRADICTION
                      </span>
                      <span className="text-xs font-bold font-mono text-on-surface">
                        {c.rule_id}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container-low text-on-surface border border-outline-variant/40">
                        {c.mechanism === "numeric"
                          ? "Mechanism 1: Rule-Based (100% confidence)"
                          : `Mechanism 2: NLI (${Math.round(c.confidence * 100)}% confidence)`}
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      {getStatusBadge(c.status)}
                    </div>
                  </div>

                  {/* Side-by-Side Comparison Box */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {/* Requirement 1 */}
                    <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/40 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <Link
                          href={`/requirements?doc=${selectedDocId}&req=${c.requirement_id_1}`}
                          className="text-xs font-mono font-bold text-secondary hover:underline flex items-center gap-1"
                        >
                          <span>{c.req_key_1}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                        {c.constraint_1 && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                            {c.constraint_1.range_display}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-on-surface leading-relaxed">
                        {c.text_1}
                      </p>
                    </div>

                    {/* Requirement 2 */}
                    <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/40 flex flex-col gap-1.5">
                      <div className="flex items-center justify-between">
                        <Link
                          href={`/requirements?doc=${selectedDocId}&req=${c.requirement_id_2}`}
                          className="text-xs font-mono font-bold text-secondary hover:underline flex items-center gap-1"
                        >
                          <span>{c.req_key_2}</span>
                          <ExternalLink className="w-3 h-3" />
                        </Link>
                        {c.constraint_2 && (
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-semibold">
                            {c.constraint_2.range_display}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-on-surface leading-relaxed">
                        {c.text_2}
                      </p>
                    </div>
                  </div>

                  {/* Violation Explanation & Suggestion */}
                  <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-rose-700 tracking-wider block mb-0.5">
                        Logical Conflict Analysis
                      </span>
                      <p className="text-on-surface-variant leading-relaxed">
                        {c.human_explanation}
                      </p>
                    </div>

                    {c.suggestion && (
                      <div className="pt-1.5 border-t border-outline-variant/30">
                        <span className="text-[10px] uppercase font-semibold text-secondary tracking-wider block mb-0.5">
                          Engineering Remediation Recommendation
                        </span>
                        <p className="text-secondary font-mono text-[11px]">
                          {c.suggestion}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* On-Demand Captum Token Attribution Strip (for semantic contradictions) */}
                  {c.mechanism === "semantic" && c.issue_id && (
                    <div className="flex flex-col gap-2 pt-1 border-t border-outline-variant/30">
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase font-semibold text-outline tracking-wider">
                          Explainability (Captum Integrated Gradients)
                        </span>
                        {!attributionsMap[c.issue_id] && (
                          <button
                            onClick={() => handleExplain(c.issue_id!)}
                            disabled={explainingIssueId === c.issue_id}
                            className="px-2.5 py-1 text-[11px] font-medium rounded bg-surface-container-high hover:bg-surface-container text-on-surface border border-outline-variant/50 transition-colors flex items-center gap-1.5"
                          >
                            <Sparkles className="w-3 h-3 text-secondary" />
                            <span>
                              {explainingIssueId === c.issue_id
                                ? "Calculating attributions..."
                                : "Explain This Finding"}
                            </span>
                          </button>
                        )}
                      </div>

                      {attributionsMap[c.issue_id] && (
                        <div className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/30 flex flex-col gap-1.5">
                          <span className="text-[10px] text-outline font-mono">
                            Token-level influence on contradiction class:
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {attributionsMap[c.issue_id].map((t, tIdx) => (
                              <span
                                key={tIdx}
                                className={`text-[11px] font-mono px-1.5 py-0.5 rounded border ${
                                  t.attribution < 0
                                    ? "bg-rose-50 text-rose-800 border-rose-200"
                                    : "bg-emerald-50 text-emerald-800 border-emerald-200"
                                }`}
                                title={`Attribution score: ${t.attribution}`}
                              >
                                {t.token}{" "}
                                <span className="opacity-70 text-[9px]">
                                  ({t.attribution > 0 ? `+${t.attribution}` : t.attribution})
                                </span>
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Review Actions if an issue_id exists */}
                  {c.issue_id && (
                    <div className="flex items-center justify-between pt-2 border-t border-outline-variant/30 text-xs">
                      <span className="text-[11px] text-outline">
                        Human-in-the-Loop Action:
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleReview(c.issue_id!, "accept")}
                          className="px-2.5 py-1 text-xs rounded border border-emerald-300 text-emerald-800 bg-emerald-50 hover:bg-emerald-100 flex items-center gap-1 font-medium transition-colors"
                        >
                          <Check className="w-3 h-3" />
                          <span>Accept</span>
                        </button>
                        <button
                          onClick={() => handleReview(c.issue_id!, "reject")}
                          className="px-2.5 py-1 text-xs rounded border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 flex items-center gap-1 font-medium transition-colors"
                        >
                          <X className="w-3 h-3" />
                          <span>Reject</span>
                        </button>
                        <Link
                          href={`/requirements?doc=${selectedDocId}&req=${c.requirement_id_1}`}
                          className="px-2.5 py-1 text-xs rounded border border-outline-variant/60 text-on-surface hover:bg-surface-container-low flex items-center gap-1 font-medium transition-colors"
                        >
                          <Edit3 className="w-3 h-3" />
                          <span>Edit Statement</span>
                        </Link>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )
      ) : activeTab === "clusters" ? (
        /* ========================================================= */
        /* TAB 4: THEMATIC CLUSTERS (TIER 3 - PHASE 15B)             */
        /* ========================================================= */
        clusters.length === 0 ? (
          <EmptyState
            title="No requirement clusters generated"
            description="Extract requirements from this document to inspect functional clusters."
            icon={<Layers className="w-6 h-6 text-outline" />}
          />
        ) : (
          <div className="flex flex-col gap-4">
            <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-xl text-xs text-on-surface flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-indigo-700" />
                <span>
                  Grouped <strong>{requirements.length} requirements</strong> into{" "}
                  <strong>{clusters.length} functional clusters</strong> using sentence embeddings and TF-IDF topic keyword extraction.
                </span>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {clusters.map((cluster) => (
                <div
                  key={cluster.cluster_id}
                  className="p-4 rounded-xl border border-outline-variant/60 bg-surface-container-lowest shadow-xs flex flex-col gap-3"
                >
                  <div className="flex items-center justify-between gap-2 pb-2 border-b border-outline-variant/40">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-800 font-mono text-xs font-bold flex items-center justify-center">
                        {cluster.cluster_id + 1}
                      </span>
                      <span className="font-semibold text-xs text-on-surface">
                        {cluster.label}
                      </span>
                    </div>
                    <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/40">
                      {cluster.size} requirement{cluster.size > 1 ? "s" : ""}
                    </span>
                  </div>

                  <div className="flex flex-wrap gap-1.5 py-1">
                    {cluster.keywords.map((kw, ki) => (
                      <span
                        key={ki}
                        className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200"
                      >
                        #{kw}
                      </span>
                    ))}
                  </div>

                  <div className="flex flex-col gap-2 pt-1">
                    {cluster.requirements.map((r) => (
                      <div
                        key={r.id}
                        className="p-2.5 rounded-lg bg-surface-container-low border border-outline-variant/30 text-xs flex flex-col gap-1"
                      >
                        <div className="flex items-center justify-between">
                          <Link
                            href={`/requirements?doc=${selectedDocId}&req=${r.id}`}
                            className="font-mono font-bold text-primary text-[11px] hover:underline flex items-center gap-1"
                          >
                            <span>{r.req_key}</span>
                            <ExternalLink className="w-2.5 h-2.5 text-outline" />
                          </Link>
                          {r.classification_label && (
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-surface-container text-on-surface-variant font-mono">
                              {r.classification_label}
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-on-surface leading-relaxed">
                          {r.text}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )
      ) : (
        /* ========================================================= */
        /* TABS 1 & 4: GENERAL FINDINGS / AMBIGUITY / READABILITY    */
        /* ========================================================= */
        filteredIssues.length === 0 ? (
          <EmptyState
            title="No findings match current filters"
            description="Try changing the category tab, clearing your search query, or changing the status filter."
            actionLabel="Reset Filters"
            onAction={() => {
              setSearchQuery("");
              setSeverityFilter("all");
              setStatusFilter("all");
            }}
            icon={<AlertCircle className="w-6 h-6 text-outline" />}
          />
        ) : (
          <div className="flex flex-col gap-3">
            {filteredIssues.map((issue) => {
              const exp = issue.explanation as any;
              const reqText = (issue.req_key ? reqTextMap.get(issue.req_key) : null) || "";
              const isEditing = editingIssueId === issue.id;

              return (
                <div
                  key={issue.id}
                  className="p-4 rounded-xl border border-outline-variant/60 bg-surface-container-lowest shadow-xs flex flex-col gap-3"
                >
                  {/* Issue Header */}
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Link
                        href={`/requirements?doc=${selectedDocId}&req=${issue.requirement_id}`}
                        className="font-mono font-bold text-xs text-on-surface bg-surface-container-low px-2 py-0.5 rounded hover:text-secondary transition-colors"
                      >
                        {issue.req_key}
                      </Link>
                      {getSeverityBadge(issue.severity)}
                      <span className="text-xs font-semibold text-on-surface">
                        {issue.type}
                      </span>
                      {exp?.confidence && (
                        <span className="text-[10px] font-mono text-outline">
                          Confidence: {Math.round(exp.confidence * 100)}%
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      {getStatusBadge(issue.status)}
                    </div>
                  </div>

                  {/* Statement Box with Highlight */}
                  {reqText && (
                    <div className="p-3 rounded-lg bg-surface-container-low/60 border border-outline-variant/40 text-xs text-on-surface leading-relaxed">
                      {reqText}
                    </div>
                  )}

                  {/* Explanation & Suggestion */}
                  <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col gap-2 text-xs">
                    <div>
                      <span className="text-[10px] uppercase font-semibold text-outline tracking-wider block mb-0.5">
                        Violation / Human Explanation
                      </span>
                      <p className="text-on-surface-variant leading-relaxed">
                        {exp?.human_explanation || "Quality defect identified by automated deterministic rule."}
                      </p>
                    </div>

                    {exp?.suggestion && (
                      <div className="pt-1.5 border-t border-outline-variant/30">
                        <span className="text-[10px] uppercase font-semibold text-outline tracking-wider block mb-0.5">
                          Remediation Recommendation
                        </span>
                        <p className="text-secondary font-mono text-[11px]">
                          {exp.suggestion}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Inline Edit or Action Buttons */}
                  {isEditing ? (
                    <div className="flex flex-col gap-2 pt-1 border-t border-outline-variant/30">
                      <span className="text-[10px] uppercase font-semibold text-outline">
                        Edit Requirement Statement Directly
                      </span>
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        className="w-full p-2 text-xs rounded-lg border border-secondary bg-surface-container-lowest text-on-surface focus:outline-none"
                      />
                      <div className="flex items-center gap-2 justify-end">
                        <button
                          onClick={() => setEditingIssueId(null)}
                          className="px-3 py-1 text-xs rounded border border-outline-variant/60 text-outline hover:text-on-surface"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleReview(issue.id, "edit")}
                          className="px-3 py-1 text-xs rounded bg-primary text-on-primary hover:bg-primary-container font-medium"
                        >
                          Save & Update Statement
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between pt-2 border-t border-outline-variant/30 text-xs">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => handleReview(issue.id, "accept")}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded bg-surface-container hover:bg-emerald-50 hover:text-emerald-800 hover:border-emerald-300 border border-outline-variant/50 text-[11px] font-medium transition-colors"
                        >
                          <Check className="w-3 h-3 text-emerald-600" />
                          <span>Accept</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => handleReview(issue.id, "reject")}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded bg-surface-container hover:bg-rose-50 hover:text-rose-800 hover:border-rose-300 border border-outline-variant/50 text-[11px] font-medium transition-colors"
                        >
                          <X className="w-3 h-3 text-rose-600" />
                          <span>Reject</span>
                        </button>

                        <button
                          type="button"
                          onClick={() => {
                            setEditingIssueId(issue.id);
                            setEditText(reqText);
                          }}
                          className="inline-flex items-center gap-1 px-3 py-1 rounded bg-surface-container hover:bg-indigo-50 hover:text-indigo-800 hover:border-indigo-300 border border-outline-variant/50 text-[11px] font-medium transition-colors"
                        >
                          <Edit3 className="w-3 h-3 text-indigo-600" />
                          <span>Edit</span>
                        </button>
                      </div>

                      <Link
                        href={`/requirements?doc=${selectedDocId}&req=${issue.requirement_id}`}
                        className="text-outline hover:text-secondary flex items-center gap-1 text-[11px]"
                      >
                        <span>Inspect Details</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )
      )}
    </div>
  );
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading Analysis Module..." className="py-20" />}>
      <AnalysisPageContent />
    </Suspense>
  );
}
