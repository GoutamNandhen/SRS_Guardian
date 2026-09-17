"use client";

import React, { useEffect, useState, useMemo } from "react";
import Link from "next/link";
import {
  FileText,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  ArrowRight,
  Upload,
  FileSpreadsheet,
  Layers,
  ChevronDown,
  ExternalLink,
  Activity,
  Award,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  DocumentQualitySummary,
  Issue,
  Requirement,
} from "@/types";

export default function DashboardPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);

  const [qualitySummary, setQualitySummary] = useState<DocumentQualitySummary | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [requirements, setRequirements] = useState<Requirement[]>([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch documents list on mount
  useEffect(() => {
    async function loadDocuments() {
      try {
        setLoading(true);
        setError(null);
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length > 0) {
          // Select first analyzed doc, or first available doc
          const analyzed = docs.find((d) => d.status === "analyzed");
          setSelectedDocId(analyzed ? analyzed.id : docs[0].id);
        }
      } catch (err: any) {
        setError(err.message || "Failed to load document index");
      } finally {
        setLoading(false);
      }
    }
    loadDocuments();
  }, []);

  // 2. Fetch quality metrics, issues, and requirements when selectedDocId changes
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadDocumentData() {
      try {
        setLoading(true);
        setError(null);

        const [quality, docIssues, reqs] = await Promise.all([
          api.getDocumentQuality(selectedDocId!).catch(() => null),
          api.getDocumentIssues(selectedDocId!).catch(() => []),
          api.getDocumentRequirements(selectedDocId!).catch(() => []),
        ]);

        setQualitySummary(quality);
        setIssues(docIssues);
        setRequirements(reqs);
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard statistics");
      } finally {
        setLoading(false);
      }
    }

    loadDocumentData();
  }, [selectedDocId]);

  // Selected document info
  const selectedDoc = useMemo(() => {
    return documents.find((d) => d.id === selectedDocId);
  }, [documents, selectedDocId]);

  // Calculate Functional vs Non-Functional counts
  const typeBreakdown = useMemo(() => {
    let functional = 0;
    let nonFunctional = 0;
    requirements.forEach((r) => {
      if (r.classification_label === "Functional") functional++;
      else if (r.classification_label === "Non-Functional") nonFunctional++;
    });
    const total = functional + nonFunctional || requirements.length || 1;
    return {
      functional,
      nonFunctional,
      functionalPct: Math.round((functional / total) * 100),
      nonFunctionalPct: Math.round((nonFunctional / total) * 100),
      total: requirements.length,
    };
  }, [requirements]);

  // Calculate Human Review progress
  const reviewProgress = useMemo(() => {
    if (issues.length === 0) return { reviewed: 0, total: 0, pct: 100 };
    const reviewed = issues.filter(
      (i) => i.status === "accepted" || i.status === "rejected" || i.status === "edited"
    ).length;
    return {
      reviewed,
      total: issues.length,
      pct: Math.round((reviewed / issues.length) * 100),
    };
  }, [issues]);

  // Categorize issues by type / module
  const issueCategories = useMemo(() => {
    const counts: Record<string, number> = {
      Ambiguity: 0,
      "Semantic Duplicates": 0,
      Contradictions: 0,
      Readability: 0,
    };

    issues.forEach((i) => {
      if (i.module === "ambiguity" || i.type.includes("WEAK") || i.type.includes("AMB")) {
        counts["Ambiguity"]++;
      } else if (i.module === "duplicates" || i.type.includes("DUPLICATE")) {
        counts["Semantic Duplicates"]++;
      } else if (i.module === "contradiction" || i.type.includes("CONTRADICTION") || i.type.includes("CONFLICT")) {
        counts["Contradictions"]++;
      } else if (i.module === "readability" || i.type.includes("READABILITY")) {
        counts["Readability"]++;
      } else {
        counts["Other"] = (counts["Other"] || 0) + 1;
      }
    });

    return counts;
  }, [issues]);

  // Score distribution percentages
  const distributionData = useMemo(() => {
    if (!qualitySummary?.distribution) {
      return [
        { label: "90-100", count: 0, pct: 0, color: "bg-emerald-600" },
        { label: "70-89", count: 0, pct: 0, color: "bg-primary" },
        { label: "50-69", count: 0, pct: 0, color: "bg-amber-500" },
        { label: "<50", count: 0, pct: 0, color: "bg-rose-600" },
      ];
    }
    const dist = qualitySummary.distribution;
    const total = qualitySummary.total_requirements || 1;
    return [
      {
        label: "90-100",
        count: dist["90-100"] || 0,
        pct: Math.round(((dist["90-100"] || 0) / total) * 100),
        color: "bg-emerald-600",
      },
      {
        label: "70-89",
        count: dist["70-89"] || 0,
        pct: Math.round(((dist["70-89"] || 0) / total) * 100),
        color: "bg-indigo-600",
      },
      {
        label: "50-69",
        count: dist["50-69"] || 0,
        pct: Math.round(((dist["50-69"] || 0) / total) * 100),
        color: "bg-amber-500",
      },
      {
        label: "<50",
        count: dist["<50"] || 0,
        pct: Math.round(((dist["<50"] || 0) / total) * 100),
        color: "bg-rose-600",
      },
    ];
  }, [qualitySummary]);

  return (
    <div className="flex flex-col gap-5 max-w-7xl mx-auto w-full">
      {/* Top Header & Document Picker */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            Dashboard
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            ISO/IEC/IEEE 29148 Requirements Engineering & Verification Overview
          </p>
        </div>

        {/* Action Controls & Document Selector */}
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

          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-surface-container-low border border-outline-variant/60 hover:bg-surface-container text-on-surface text-xs font-medium transition-colors shadow-xs"
          >
            <Upload className="w-3.5 h-3.5 text-outline" />
            <span>Upload SRS</span>
          </Link>

          {selectedDocId && (
            <Link
              href={`/reports?doc=${selectedDocId}`}
              className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-primary text-on-primary hover:bg-primary-container text-xs font-medium transition-colors shadow-xs"
            >
              <FileSpreadsheet className="w-3.5 h-3.5" />
              <span>Export Report</span>
            </Link>
          )}
        </div>
      </div>

      {loading && !qualitySummary ? (
        <LoadingState message="Calculating requirement analytics..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
      ) : documents.length === 0 ? (
        <EmptyState
          title="No specifications uploaded yet"
          description="Upload an SRS document in PDF, DOCX, or plain text to view automated ISO 29148 analytics, score distributions, and defect clusters."
          actionLabel="Upload Specification"
          onAction={() => (window.location.href = "/documents")}
          icon={<FileText className="w-6 h-6 text-outline" />}
        />
      ) : (
        <>
          {/* Row of 4 Compact KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
            {/* KPI 1: Total Requirements */}
            <div className="bg-surface-container-lowest rounded-xl p-3.5 border border-outline-variant/50 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                  Total Requirements
                </span>
                <Layers className="w-4 h-4 text-outline" />
              </div>
              <div className="mt-2.5 flex items-baseline justify-between">
                <span className="text-2xl font-bold font-mono tracking-tight text-on-surface">
                  {qualitySummary?.total_requirements ?? requirements.length}
                </span>
                <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant">
                  100% parsed
                </span>
              </div>
              <span className="text-[11px] text-outline mt-1 truncate">
                {selectedDoc?.filename}
              </span>
            </div>

            {/* KPI 2: Average Quality Score */}
            <div className="bg-surface-container-lowest rounded-xl p-3.5 border border-outline-variant/50 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                  Average Quality Score
                </span>
                <TrendingUp className="w-4 h-4 text-secondary" />
              </div>
              <div className="mt-2.5 flex items-baseline justify-between">
                <div className="flex items-baseline gap-1">
                  <span className="text-2xl font-bold font-mono tracking-tight text-on-surface">
                    {qualitySummary?.mean_score ? qualitySummary.mean_score.toFixed(1) : "—"}
                  </span>
                  <span className="text-xs text-outline font-mono">/100</span>
                </div>
                <span
                  className={`text-[11px] font-medium px-2 py-0.5 rounded border ${
                    (qualitySummary?.mean_score ?? 0) >= 80
                      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                      : (qualitySummary?.mean_score ?? 0) >= 60
                      ? "bg-amber-50 text-amber-800 border-amber-200"
                      : "bg-rose-50 text-rose-800 border-rose-200"
                  }`}
                >
                  {(qualitySummary?.mean_score ?? 0) >= 80 ? "Passing Grade" : "Needs Review"}
                </span>
              </div>
              <span className="text-[11px] text-outline mt-1 truncate">
                Target: ≥80.0 deterministic standard
              </span>
            </div>

            {/* KPI 3: Open Findings / Defects */}
            <div className="bg-surface-container-lowest rounded-xl p-3.5 border border-outline-variant/50 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                  Potential Findings
                </span>
                <AlertTriangle className="w-4 h-4 text-amber-600" />
              </div>
              <div className="mt-2.5 flex items-baseline justify-between">
                <span className="text-2xl font-bold font-mono tracking-tight text-on-surface">
                  {issues.length}
                </span>
                <div className="flex items-center gap-1.5 text-[10px] font-mono">
                  <span className="text-rose-700 font-semibold">
                    •{issues.filter((i) => i.severity === "error").length} crit
                  </span>
                  <span className="text-amber-700 font-semibold">
                    •{issues.filter((i) => i.severity === "warning").length} warn
                  </span>
                </div>
              </div>
              <span className="text-[11px] text-outline mt-1 truncate">
                Ambiguity, duplicate & syntax checks
              </span>
            </div>

            {/* KPI 4: Human Review Progress */}
            <div className="bg-surface-container-lowest rounded-xl p-3.5 border border-outline-variant/50 shadow-xs flex flex-col justify-between">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                  Human Review Status
                </span>
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="mt-2.5 flex items-baseline justify-between">
                <span className="text-2xl font-bold font-mono tracking-tight text-on-surface">
                  {reviewProgress.pct}%
                </span>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {reviewProgress.reviewed}/{reviewProgress.total} closed
                </span>
              </div>
              <span className="text-[11px] text-outline mt-1 truncate">
                Human-in-the-loop verification
              </span>
            </div>
          </div>

          {/* Main 2-Column Analytics Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
            {/* ========================================================= */}
            {/* LEFT COLUMN: Quality Distributions (~60% / 7 cols)        */}
            {/* ========================================================= */}
            <div className="lg:col-span-7 flex flex-col gap-4">
              {/* Card 1: Quality Score Distribution */}
              <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/50 shadow-xs flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
                  <div>
                    <h2 className="text-sm font-bold text-on-surface">
                      Quality Score Distribution
                    </h2>
                    <p className="text-[11px] text-outline">
                      Requirements stratified across standard rating intervals
                    </p>
                  </div>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-surface-container text-on-surface-variant">
                    ISO 29148 Standard
                  </span>
                </div>

                {/* Histogram Bars */}
                <div className="pt-5 pb-2 flex flex-col gap-3">
                  {distributionData.map((d, i) => (
                    <div key={i} className="flex flex-col gap-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-mono font-medium text-on-surface">
                          Score Tier: {d.label}
                        </span>
                        <span className="font-mono text-outline">
                          {d.count} reqs ({d.pct}%)
                        </span>
                      </div>
                      <div className="w-full h-2 rounded-full bg-surface-container overflow-hidden">
                        <div
                          className={`h-full rounded-full ${d.color}`}
                          style={{ width: `${Math.max(d.pct, d.count > 0 ? 5 : 0)}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-3 mt-1 border-t border-outline-variant/30 text-[11px] text-on-surface-variant">
                  <span>Median: {qualitySummary?.median_score ?? "—"}/100</span>
                  <span className="text-secondary font-medium font-mono">
                    Passing: ≥80 pts
                  </span>
                </div>
              </div>

              {/* Card 2: Issues by Defect Category */}
              <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/50 shadow-xs flex flex-col">
                <div className="flex items-center justify-between pb-3 border-b border-outline-variant/30">
                  <div>
                    <h2 className="text-sm font-bold text-on-surface">
                      Findings by Rule Category
                    </h2>
                    <p className="text-[11px] text-outline">
                      Syntactic, ambiguity, and redundancy defect clusters
                    </p>
                  </div>
                  <span className="text-[10px] font-mono text-outline">
                    {issues.length} Total Detected
                  </span>
                </div>

                <div className="flex flex-col gap-3 pt-3">
                  {Object.entries(issueCategories).map(([cat, cnt]) => {
                    const pct = issues.length > 0 ? Math.round((cnt / issues.length) * 100) : 0;
                    return (
                      <div key={cat} className="flex flex-col gap-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-medium text-on-surface">{cat}</span>
                          <span className="font-mono text-outline">
                            {cnt} issues ({pct}%)
                          </span>
                        </div>
                        <div className="w-full h-1.5 rounded-full bg-surface-container overflow-hidden">
                          <div
                            className="h-full bg-secondary rounded-full"
                            style={{ width: `${pct}%` }}
                          ></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* ========================================================= */}
            {/* RIGHT COLUMN: Types Donut & Lowest Scoring (~40% / 5 cols) */}
            {/* ========================================================= */}
            <div className="lg:col-span-5 flex flex-col gap-4">
              {/* Card 3: Functional Breakdown */}
              <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/50 shadow-xs flex flex-col">
                <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
                  <h2 className="text-sm font-bold text-on-surface">
                    Requirement Classification
                  </h2>
                  <span className="text-[10px] text-outline font-mono">TF-IDF + LR</span>
                </div>

                {/* Donut Graphic */}
                <div className="flex items-center justify-center py-4 relative">
                  <svg className="w-28 h-28 -rotate-90" viewBox="0 0 120 120">
                    <circle
                      cx="60"
                      cy="60"
                      r="45"
                      fill="transparent"
                      stroke="#e2e8f0"
                      strokeWidth="14"
                    />
                    <circle
                      cx="60"
                      cy="60"
                      r="45"
                      fill="transparent"
                      stroke="#4b41e1"
                      strokeWidth="14"
                      strokeDasharray="282.7"
                      strokeDashoffset={282.7 - (282.7 * typeBreakdown.functionalPct) / 100}
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-base font-bold font-mono text-on-surface">
                      {typeBreakdown.total}
                    </span>
                    <span className="text-[9px] uppercase tracking-wider text-outline">
                      Reqs
                    </span>
                  </div>
                </div>

                {/* Legend */}
                <div className="grid grid-cols-2 gap-2 pt-1 text-center text-xs">
                  <div className="p-2 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col items-center">
                    <div className="flex items-center gap-1 text-[11px] text-on-surface mb-0.5">
                      <span className="w-2 h-2 rounded-full bg-secondary"></span>
                      <span>Functional</span>
                    </div>
                    <span className="font-bold font-mono text-on-surface">
                      {typeBreakdown.functional} ({typeBreakdown.functionalPct}%)
                    </span>
                  </div>

                  <div className="p-2 rounded-lg bg-surface-container-low border border-outline-variant/40 flex flex-col items-center">
                    <div className="flex items-center gap-1 text-[11px] text-on-surface mb-0.5">
                      <span className="w-2 h-2 rounded-full bg-slate-300"></span>
                      <span>Non-Functional</span>
                    </div>
                    <span className="font-bold font-mono text-on-surface">
                      {typeBreakdown.nonFunctional} ({typeBreakdown.nonFunctionalPct}%)
                    </span>
                  </div>
                </div>
              </div>

              {/* Card 4: Lowest Scoring Requirements */}
              <div className="bg-surface-container-lowest rounded-xl p-4 border border-outline-variant/50 shadow-xs flex flex-col">
                <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
                  <div>
                    <h2 className="text-sm font-bold text-on-surface">
                      Lowest Scoring Requirements
                    </h2>
                    <p className="text-[10px] text-outline">
                      Priority candidates for engineer review
                    </p>
                  </div>
                  <span className="text-[10px] font-mono text-rose-700 bg-rose-50 px-1.5 py-0.5 rounded border border-rose-200">
                    Action Items
                  </span>
                </div>

                <div className="divide-y divide-outline-variant/20 pt-1">
                  {(qualitySummary?.worst_requirements ?? []).slice(0, 5).map((w) => (
                    <Link
                      key={w.requirement_id}
                      href={`/requirements?doc=${selectedDocId}&req=${w.requirement_id}`}
                      className="py-2.5 flex items-start justify-between gap-2 hover:bg-surface-container-low/50 px-1 rounded transition-colors group"
                    >
                      <div className="flex flex-col flex-1 pr-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-xs font-mono font-bold text-on-surface group-hover:text-secondary transition-colors">
                            {w.req_key}
                          </span>
                          {w.issues_count > 0 && (
                            <span className="text-[9px] text-amber-700 font-mono">
                              ({w.issues_count} issues)
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-on-surface-variant line-clamp-1 mt-0.5">
                          {w.text}
                        </p>
                      </div>

                      <div className="flex items-center gap-1.5 flex-shrink-0">
                        <span
                          className={`text-xs font-mono font-bold px-1.5 py-0.5 rounded border ${
                            w.overall_score >= 80
                              ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                              : w.overall_score >= 60
                              ? "bg-amber-50 text-amber-800 border-amber-200"
                              : "bg-rose-50 text-rose-800 border-rose-200"
                          }`}
                        >
                          {Math.round(w.overall_score)}
                        </span>
                        <ArrowRight className="w-3 h-3 text-outline group-hover:text-secondary group-hover:translate-x-0.5 transition-all" />
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
