"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  GitCompare,
  ArrowRight,
  Plus,
  Minus,
  RotateCcw,
  Equal,
  CheckCircle2,
  AlertTriangle,
  Search,
  Filter,
  Layers,
  TrendingUp,
  TrendingDown,
  ShieldCheck,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  DocumentComparisonResponse,
  RequirementComparisonItem,
} from "@/types";

export default function ComparePage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [doc1Id, setDoc1Id] = useState<number | null>(null);
  const [doc2Id, setDoc2Id] = useState<number | null>(null);

  const [comparison, setComparison] = useState<DocumentComparisonResponse | null>(null);
  const [loadingDocs, setLoadingDocs] = useState(true);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<"all" | "modified" | "added" | "removed" | "unchanged">("all");
  const [searchQuery, setSearchQuery] = useState("");

  // Load document list on mount
  useEffect(() => {
    async function loadDocuments() {
      try {
        setLoadingDocs(true);
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length >= 2) {
          setDoc1Id(docs[0].id);
          setDoc2Id(docs[1].id);
        } else if (docs.length === 1) {
          setDoc1Id(docs[0].id);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load document list");
      } finally {
        setLoadingDocs(false);
      }
    }
    loadDocuments();
  }, []);

  // Run comparison when doc1Id & doc2Id are valid
  const handleCompare = async () => {
    if (!doc1Id || !doc2Id) return;
    if (doc1Id === doc2Id) {
      setError("Please select two distinct documents or versions to compare.");
      return;
    }
    try {
      setComparing(true);
      setError(null);
      const res = await api.compareDocuments(doc1Id, doc2Id);
      setComparison(res);
    } catch (err: any) {
      setError(err.message || "Comparison failed between selected documents");
      setComparison(null);
    } finally {
      setComparing(false);
    }
  };

  // Auto-compare on initial selection if both are preset
  useEffect(() => {
    if (doc1Id && doc2Id && doc1Id !== doc2Id && !comparison && !comparing) {
      handleCompare();
    }
  }, [doc1Id, doc2Id]);

  // Filter comparison items
  const filteredItems = useMemo(() => {
    if (!comparison) return [];
    return comparison.items.filter((item) => {
      if (statusFilter !== "all" && item.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const keyMatch = item.req_key.toLowerCase().includes(q);
        const v1Match = item.text_v1 ? item.text_v1.toLowerCase().includes(q) : false;
        const v2Match = item.text_v2 ? item.text_v2.toLowerCase().includes(q) : false;
        return keyMatch || v1Match || v2Match;
      }
      return true;
    });
  }, [comparison, statusFilter, searchQuery]);

  if (loadingDocs) {
    return <LoadingState message="Loading documents for revision comparison..." />;
  }

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto text-on-surface">
      {/* Header */}
      <div className="pb-3 border-b border-outline-variant/30 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface flex items-center gap-2">
            <GitCompare className="w-5 h-5 text-primary" />
            <span>Version Comparison & Semantic Diffing</span>
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Trace requirement evolution, quality score shifts, resolved defects, and introduced issues across SRS revisions.
          </p>
        </div>
      </div>

      {/* Document Selectors Control Bar */}
      <div className="p-4 rounded-xl border border-outline-variant/50 bg-surface-container-lowest shadow-xs flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-outline uppercase tracking-wider">
              Base Document (v1.0)
            </label>
            <select
              value={doc1Id || ""}
              onChange={(e) => setDoc1Id(parseInt(e.target.value, 10))}
              className="h-8 px-2.5 rounded-lg bg-surface-container-low border border-outline-variant/60 text-xs text-on-surface font-medium focus:outline-none focus:border-primary"
            >
              <option value="" disabled>Select base document</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  #{d.id} — {d.filename} ({d.requirement_count} reqs)
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center self-end mb-1 text-outline">
            <ArrowRight className="w-4 h-4" />
          </div>

          <div className="flex flex-col gap-1">
            <label className="text-[11px] font-semibold text-outline uppercase tracking-wider">
              Target Document (v2.0)
            </label>
            <select
              value={doc2Id || ""}
              onChange={(e) => setDoc2Id(parseInt(e.target.value, 10))}
              className="h-8 px-2.5 rounded-lg bg-surface-container-low border border-outline-variant/60 text-xs text-on-surface font-medium focus:outline-none focus:border-primary"
            >
              <option value="" disabled>Select target document</option>
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  #{d.id} — {d.filename} ({d.requirement_count} reqs)
                </option>
              ))}
            </select>
          </div>
        </div>

        <button
          type="button"
          onClick={handleCompare}
          disabled={!doc1Id || !doc2Id || doc1Id === doc2Id || comparing}
          className="h-8 px-4 rounded-lg bg-primary text-white font-medium hover:bg-primary/90 disabled:opacity-50 flex items-center gap-1.5 transition-colors self-end"
        >
          {comparing ? (
            <span>Diffing...</span>
          ) : (
            <>
              <GitCompare className="w-3.5 h-3.5" />
              <span>Compare Revisions</span>
            </>
          )}
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={handleCompare} />}

      {comparing && <LoadingState message="Aligning cross-version requirements and calculating semantic diffs..." />}

      {!comparing && !comparison && !error && (
        <EmptyState
          title="Select two documents to compare"
          description="Choose a baseline document and a target revision to inspect requirement modifications, score changes, and issue lifecycles."
          icon={<GitCompare className="w-6 h-6 text-outline" />}
        />
      )}

      {!comparing && comparison && (
        <>
          {/* KPI Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            {/* Added */}
            <div className="p-3.5 rounded-xl border border-emerald-200 bg-emerald-50/50 flex flex-col gap-1">
              <div className="flex items-center justify-between text-emerald-800 text-[11px] font-semibold">
                <span>Added</span>
                <Plus className="w-3.5 h-3.5" />
              </div>
              <span className="text-xl font-bold font-mono text-emerald-900">
                +{comparison.added_count}
              </span>
              <span className="text-[10px] text-emerald-700">New in v2.0</span>
            </div>

            {/* Removed */}
            <div className="p-3.5 rounded-xl border border-rose-200 bg-rose-50/50 flex flex-col gap-1">
              <div className="flex items-center justify-between text-rose-800 text-[11px] font-semibold">
                <span>Removed</span>
                <Minus className="w-3.5 h-3.5" />
              </div>
              <span className="text-xl font-bold font-mono text-rose-900">
                -{comparison.removed_count}
              </span>
              <span className="text-[10px] text-rose-700">Omitted in v2.0</span>
            </div>

            {/* Modified */}
            <div className="p-3.5 rounded-xl border border-amber-200 bg-amber-50/50 flex flex-col gap-1">
              <div className="flex items-center justify-between text-amber-800 text-[11px] font-semibold">
                <span>Modified</span>
                <RotateCcw className="w-3.5 h-3.5" />
              </div>
              <span className="text-xl font-bold font-mono text-amber-900">
                {comparison.modified_count}
              </span>
              <span className="text-[10px] text-amber-700">Changed phrasing</span>
            </div>

            {/* Unchanged */}
            <div className="p-3.5 rounded-xl border border-blue-200 bg-blue-50/50 flex flex-col gap-1">
              <div className="flex items-center justify-between text-blue-800 text-[11px] font-semibold">
                <span>Unchanged</span>
                <Equal className="w-3.5 h-3.5" />
              </div>
              <span className="text-xl font-bold font-mono text-blue-900">
                {comparison.unchanged_count}
              </span>
              <span className="text-[10px] text-blue-700">Identical</span>
            </div>

            {/* Score Delta */}
            <div className={`p-3.5 rounded-xl border flex flex-col gap-1 ${
              comparison.score_delta > 0
                ? "border-emerald-200 bg-emerald-50/40 text-emerald-900"
                : comparison.score_delta < 0
                ? "border-rose-200 bg-rose-50/40 text-rose-900"
                : "border-outline-variant/50 bg-surface-container-lowest"
            }`}>
              <div className="flex items-center justify-between text-[11px] font-semibold">
                <span>Quality Score</span>
                {comparison.score_delta > 0 ? (
                  <TrendingUp className="w-3.5 h-3.5 text-emerald-700" />
                ) : (
                  <TrendingDown className="w-3.5 h-3.5 text-rose-700" />
                )}
              </div>
              <div className="flex items-baseline gap-1.5">
                <span className="text-xl font-bold font-mono">
                  {comparison.score_delta > 0 ? `+${comparison.score_delta}` : comparison.score_delta}
                </span>
                <span className="text-[10px] opacity-75 font-mono">
                  ({comparison.avg_score_v1} → {comparison.avg_score_v2})
                </span>
              </div>
              <span className="text-[10px] opacity-75">Net document delta</span>
            </div>

            {/* Defect Lifecycle */}
            <div className="p-3.5 rounded-xl border border-indigo-200 bg-indigo-50/40 flex flex-col gap-1">
              <div className="flex items-center justify-between text-indigo-800 text-[11px] font-semibold">
                <span>Issues Life</span>
                <ShieldCheck className="w-3.5 h-3.5 text-indigo-700" />
              </div>
              <div className="flex items-baseline gap-2 font-mono text-xs">
                <span className="text-emerald-700 font-bold">-{comparison.total_resolved_issues} resolved</span>
                <span className="text-rose-700 font-bold">+{comparison.total_new_issues} new</span>
              </div>
              <span className="text-[10px] text-indigo-700">Evolution status</span>
            </div>
          </div>

          {/* Filter Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-surface-container-lowest rounded-xl border border-outline-variant/50 shadow-xs text-xs">
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => setStatusFilter("all")}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  statusFilter === "all" ? "bg-surface-container text-on-surface font-semibold" : "text-outline hover:text-on-surface"
                }`}
              >
                All Changes ({comparison.items.length})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter("modified")}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  statusFilter === "modified" ? "bg-amber-100 text-amber-900 font-semibold" : "text-outline hover:text-on-surface"
                }`}
              >
                Modified ({comparison.modified_count})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter("added")}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  statusFilter === "added" ? "bg-emerald-100 text-emerald-900 font-semibold" : "text-outline hover:text-on-surface"
                }`}
              >
                Added ({comparison.added_count})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter("removed")}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  statusFilter === "removed" ? "bg-rose-100 text-rose-900 font-semibold" : "text-outline hover:text-on-surface"
                }`}
              >
                Removed ({comparison.removed_count})
              </button>
              <button
                type="button"
                onClick={() => setStatusFilter("unchanged")}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  statusFilter === "unchanged" ? "bg-blue-100 text-blue-900 font-semibold" : "text-outline hover:text-on-surface"
                }`}
              >
                Unchanged ({comparison.unchanged_count})
              </button>
            </div>

            <div className="relative flex items-center w-56 h-7 px-2 rounded-lg bg-surface-container-low border border-outline-variant/60 focus-within:border-primary transition-all">
              <Search className="w-3 h-3 text-outline mr-1.5 flex-shrink-0" />
              <input
                type="text"
                placeholder="Search requirements..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-transparent border-none outline-none text-xs text-on-surface placeholder:text-outline"
              />
              {searchQuery && (
                <button type="button" onClick={() => setSearchQuery("")} className="text-outline hover:text-on-surface">
                  ×
                </button>
              )}
            </div>
          </div>

          {/* Comparison Cards List */}
          <div className="flex flex-col gap-3">
            {filteredItems.length === 0 ? (
              <EmptyState
                title="No changes match current filter"
                description="Try selecting a different status filter or clearing your search term."
                icon={<Filter className="w-6 h-6 text-outline" />}
              />
            ) : (
              filteredItems.map((item, index) => {
                const isModified = item.status === "modified";
                const isAdded = item.status === "added";
                const isRemoved = item.status === "removed";
                const isUnchanged = item.status === "unchanged";

                return (
                  <div
                    key={`${item.req_key}-${index}`}
                    className={`p-4 rounded-xl border bg-surface-container-lowest shadow-xs flex flex-col gap-3 ${
                      isModified
                        ? "border-amber-200"
                        : isAdded
                        ? "border-emerald-200"
                        : isRemoved
                        ? "border-rose-200"
                        : "border-outline-variant/40 opacity-80"
                    }`}
                  >
                    {/* Item Header */}
                    <div className="flex flex-wrap items-center justify-between gap-2 pb-2 border-b border-outline-variant/30">
                      <div className="flex items-center gap-2 flex-wrap">
                        {isModified && (
                          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-amber-100 text-amber-900 border border-amber-300">
                            MODIFIED
                          </span>
                        )}
                        {isAdded && (
                          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-300">
                            + ADDED IN TARGET
                          </span>
                        )}
                        {isRemoved && (
                          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-rose-100 text-rose-900 border border-rose-300">
                            - REMOVED FROM TARGET
                          </span>
                        )}
                        {isUnchanged && (
                          <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-blue-100 text-blue-900 border border-blue-200">
                            = UNCHANGED
                          </span>
                        )}

                        <span className="font-mono font-bold text-xs text-on-surface">
                          {item.req_key}
                        </span>

                        {item.similarity !== null && item.similarity !== undefined && item.similarity > 0 && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container text-outline border border-outline-variant/40">
                            Semantic Similarity: {Math.round(item.similarity * 100)}%
                          </span>
                        )}
                      </div>

                      {/* Quality Score Delta */}
                      {item.score_v1 !== null && item.score_v2 !== null && (
                        <div className="flex items-center gap-1.5 text-xs font-mono">
                          <span className="text-outline">Score:</span>
                          <span className="font-medium text-on-surface-variant">{item.score_v1}</span>
                          <span className="text-outline">→</span>
                          <span className="font-medium text-on-surface">{item.score_v2}</span>
                          {item.score_delta !== null && item.score_delta !== undefined && item.score_delta !== 0 && (
                            <span
                              className={`font-bold ml-1 px-1.5 py-0.2 rounded text-[11px] ${
                                item.score_delta > 0
                                  ? "bg-emerald-100 text-emerald-800"
                                  : "bg-rose-100 text-rose-800"
                              }`}
                            >
                              {item.score_delta > 0 ? `+${item.score_delta}` : item.score_delta}
                            </span>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Side-by-Side Phrasing */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      {/* Version 1 */}
                      <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 flex flex-col gap-1.5">
                        <div className="flex items-center justify-between text-[11px] font-semibold text-outline">
                          <span>Base Version ({comparison.doc1_filename})</span>
                          {item.score_v1 !== null && (
                            <span className="font-mono text-[10px]">Score: {item.score_v1}</span>
                          )}
                        </div>
                        <p className="text-xs text-on-surface leading-relaxed">
                          {item.text_v1 || <span className="italic text-outline">Not present in base document</span>}
                        </p>
                      </div>

                      {/* Version 2 */}
                      <div className="p-3 rounded-lg bg-surface-container-low border border-outline-variant/30 flex flex-col gap-1.5">
                        <div className="flex items-center justify-between text-[11px] font-semibold text-outline">
                          <span>Target Version ({comparison.doc2_filename})</span>
                          {item.score_v2 !== null && (
                            <span className="font-mono text-[10px]">Score: {item.score_v2}</span>
                          )}
                        </div>
                        <p className="text-xs text-on-surface leading-relaxed">
                          {item.text_v2 || <span className="italic text-outline">Omitted in target document</span>}
                        </p>
                      </div>
                    </div>

                    {/* Inline Diff Highlights if modified */}
                    {isModified && item.diff_text && (
                      <div className="p-2.5 rounded-lg bg-surface-container-lowest border border-amber-200 text-xs flex flex-col gap-1">
                        <span className="text-[10px] font-semibold text-amber-800 uppercase tracking-wider">
                          Word-Level Difference
                        </span>
                        <div className="font-mono text-[11px] leading-relaxed text-on-surface">
                          {item.diff_text.split(" ").map((chunk, ci) => {
                            if (chunk.startsWith("[-") && chunk.endsWith("-]")) {
                              return (
                                <span key={ci} className="bg-rose-100 text-rose-800 line-through px-1 rounded mr-1">
                                  {chunk.slice(2, -2)}
                                </span>
                              );
                            }
                            if (chunk.startsWith("[+") && chunk.endsWith("+]")) {
                              return (
                                <span key={ci} className="bg-emerald-100 text-emerald-800 font-semibold px-1 rounded mr-1">
                                  {chunk.slice(2, -2)}
                                </span>
                              );
                            }
                            return <span key={ci} className="mr-1">{chunk}</span>;
                          })}
                        </div>
                      </div>
                    )}

                    {/* Defect Lifecycle Trace */}
                    {(item.resolved_issues.length > 0 || item.new_issues.length > 0) && (
                      <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-outline-variant/30 text-xs">
                        {item.resolved_issues.map((iss, ii) => (
                          <span
                            key={ii}
                            className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded font-mono bg-emerald-100 text-emerald-800 border border-emerald-300"
                            title={iss.human_explanation}
                          >
                            <CheckCircle2 className="w-3 h-3 text-emerald-700" />
                            <span>Resolved: {iss.rule_id}</span>
                          </span>
                        ))}
                        {item.new_issues.map((iss, ii) => (
                          <span
                            key={ii}
                            className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded font-mono bg-rose-100 text-rose-800 border border-rose-300"
                            title={iss.human_explanation}
                          >
                            <AlertCircle className="w-3 h-3 text-rose-700" />
                            <span>New Defect: {iss.rule_id}</span>
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </>
      )}
    </div>
  );
}
