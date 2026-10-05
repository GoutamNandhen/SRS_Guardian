"use client";

import React, { useEffect, useState, useMemo, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  FileText,
  FileSpreadsheet,
  Download,
  Printer,
  ExternalLink,
  ChevronDown,
  Layers,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  RefreshCw,
  Sparkles,
  ShieldCheck,
  FileCheck,
  Award,
  Eye,
} from "lucide-react";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import {
  DocumentListItem,
  DocumentQualitySummary,
  Issue,
} from "@/types";

function ReportsPageContent() {
  const searchParams = useSearchParams();
  const initialDocParam = searchParams.get("doc");

  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(
    initialDocParam ? parseInt(initialDocParam, 10) : null
  );

  const [qualitySummary, setQualitySummary] = useState<DocumentQualitySummary | null>(null);
  const [issues, setIssues] = useState<Issue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [iframeKey, setIframeKey] = useState(0);

  // 1. Fetch available documents
  useEffect(() => {
    async function loadDocs() {
      try {
        setLoading(true);
        setError(null);
        const docs = await api.getDocuments();
        setDocuments(docs);
        if (docs.length > 0) {
          if (!selectedDocId || !docs.some((d) => d.id === selectedDocId)) {
            const analyzed = docs.find((d) => d.status === "analyzed");
            setSelectedDocId(analyzed ? analyzed.id : docs[0].id);
          }
        }
      } catch (err: any) {
        setError(err.message || "Failed to load document list");
      } finally {
        setLoading(false);
      }
    }
    loadDocs();
  }, []);

  // 2. Fetch document metrics when selectedDocId changes
  useEffect(() => {
    if (!selectedDocId) return;

    async function loadDocReportData() {
      try {
        const [quality, docIssues] = await Promise.all([
          api.getDocumentQuality(selectedDocId!).catch(() => null),
          api.getDocumentIssues(selectedDocId!).catch(() => []),
        ]);
        setQualitySummary(quality);
        setIssues(docIssues);
      } catch (err: any) {
        console.error("Failed to load report summary", err);
      }
    }

    loadDocReportData();
    setIframeKey((k) => k + 1);
  }, [selectedDocId]);

  const selectedDoc = useMemo(() => {
    return documents.find((d) => d.id === selectedDocId);
  }, [documents, selectedDocId]);

  const reviewedCount = useMemo(() => {
    return issues.filter(
      (i) => i.status === "accepted" || i.status === "rejected" || i.status === "edited"
    ).length;
  }, [issues]);

  // URLs for exports
  const htmlReportUrl = selectedDocId ? api.getReportUrl(selectedDocId, "html") : "#";
  const pdfReportUrl = selectedDocId ? api.getReportUrl(selectedDocId, "pdf") : "#";
  const csvReqsUrl = selectedDocId ? api.getReportUrl(selectedDocId, "csv", "requirements") : "#";
  const csvIssuesUrl = selectedDocId ? api.getReportUrl(selectedDocId, "csv", "issues") : "#";

  return (
    <div className="flex flex-col gap-5 max-w-7xl mx-auto w-full">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 pb-3 border-b border-outline-variant/40">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold tracking-tight text-on-surface">
              Verification & Validation Reports
            </h1>
            <span className="text-xs font-mono font-medium px-2 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/50">
              ISO 29148 Standard
            </span>
          </div>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Automated requirement compliance, quality scorecards, and defect ledger export
          </p>
        </div>

        {/* Quick Actions & Document Selector */}
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
            <>
              <Link
                href={`/reports/review?doc=${selectedDocId}`}
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-secondary/10 border border-secondary/30 hover:bg-secondary/20 text-secondary text-xs font-semibold transition-colors shadow-xs"
                title="Open Phase 18 Interactive Detailed Review Report"
              >
                <Eye className="w-3.5 h-3.5 text-secondary" />
                <span>Detailed Review</span>
              </Link>

              <a
                href={htmlReportUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-surface-container-low border border-outline-variant/60 hover:bg-surface-container text-on-surface text-xs font-medium transition-colors shadow-xs"
              >
                <Printer className="w-3.5 h-3.5 text-outline" />
                <span>Print / Popout</span>
              </a>

              <a
                href={pdfReportUrl}
                download
                className="inline-flex items-center gap-1.5 h-8 px-3.5 rounded-lg bg-primary text-on-primary hover:bg-primary-container text-xs font-medium transition-colors shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download PDF</span>
              </a>
            </>
          )}
        </div>
      </div>

      {loading ? (
        <LoadingState message="Loading report generation center..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={() => setSelectedDocId(selectedDocId)} />
      ) : documents.length === 0 ? (
        <EmptyState
          title="No specifications available for report generation"
          description="Upload an SRS document in the Documents module to generate comprehensive audit scorecards."
          actionLabel="Upload Specification"
          onAction={() => (window.location.href = "/documents")}
          icon={<FileText className="w-6 h-6 text-outline" />}
        />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start w-full">
          {/* ========================================================= */}
          {/* LEFT RAIL: Configuration, Summary & Export Formats (4 cols) */}
          {/* ========================================================= */}
          <div className="lg:col-span-4 xl:col-span-4 flex flex-col gap-4">
            {/* Executive Scorecard Card */}
            <div className="p-4 rounded-xl border border-outline-variant/50 bg-surface-container-lowest shadow-xs flex flex-col gap-3">
              <div className="flex items-center justify-between pb-2 border-b border-outline-variant/30">
                <span className="text-[10px] font-semibold text-outline uppercase tracking-wider">
                  Audit Summary
                </span>
                <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded bg-emerald-50 text-emerald-800 border border-emerald-200">
                  {selectedDoc?.status.toUpperCase()}
                </span>
              </div>

              <div className="flex items-baseline justify-between pt-1">
                <div>
                  <span className="text-3xl font-black font-mono text-on-surface">
                    {qualitySummary?.mean_score ? qualitySummary.mean_score.toFixed(1) : "—"}
                  </span>
                  <span className="text-xs font-mono text-outline"> / 100</span>
                  <p className="text-[11px] text-on-surface-variant font-medium mt-0.5">
                    Mean ISO 29148 Quality Score
                  </p>
                </div>
                <div
                  className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    (qualitySummary?.mean_score ?? 0) >= 80
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-amber-100 text-amber-800"
                  }`}
                >
                  <Award className="w-5 h-5" />
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t border-outline-variant/30 text-xs">
                <div className="p-2 rounded-lg bg-surface-container-low flex flex-col">
                  <span className="text-[10px] text-outline uppercase">Requirements</span>
                  <span className="text-base font-bold font-mono text-on-surface">
                    {qualitySummary?.total_requirements ?? 0}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-surface-container-low flex flex-col">
                  <span className="text-[10px] text-outline uppercase">Total Findings</span>
                  <span className="text-base font-bold font-mono text-amber-700">
                    {issues.length}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-surface-container-low flex flex-col">
                  <span className="text-[10px] text-outline uppercase">Human Reviews</span>
                  <span className="text-base font-bold font-mono text-indigo-700">
                    {reviewedCount} / {issues.length}
                  </span>
                </div>
                <div className="p-2 rounded-lg bg-surface-container-low flex flex-col">
                  <span className="text-[10px] text-outline uppercase">Score Range</span>
                  <span className="text-base font-bold font-mono text-on-surface">
                    {qualitySummary?.min_score ? Math.round(qualitySummary.min_score) : "—"}–
                    {qualitySummary?.max_score ? Math.round(qualitySummary.max_score) : "—"}
                  </span>
                </div>
              </div>

              <div className="pt-2 text-[11px] text-outline leading-tight border-t border-outline-variant/30">
                Checks performed against machine-checkable criteria inspired by ISO/IEC/IEEE 29148:2018.
              </div>
            </div>

            {/* Export Options Card */}
            <div className="p-4 rounded-xl border border-outline-variant/50 bg-surface-container-lowest shadow-xs flex flex-col gap-3">
              <span className="text-[10px] font-semibold text-outline uppercase tracking-wider pb-1 border-b border-outline-variant/30">
                Export Artifacts & Datasets
              </span>

              <div className="flex flex-col gap-2">
                {/* PDF */}
                <a
                  href={pdfReportUrl}
                  download
                  className="p-3 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container transition-colors flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded bg-rose-100 text-rose-800 flex items-center justify-center font-mono font-bold text-xs">
                      PDF
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-on-surface">Formal Audit Report</p>
                      <p className="text-[10px] text-outline">Offline ReportLab / xhtml2pdf engine</p>
                    </div>
                  </div>
                  <Download className="w-3.5 h-3.5 text-outline group-hover:text-secondary transition-colors" />
                </a>

                {/* HTML */}
                <a
                  href={htmlReportUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="p-3 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container transition-colors flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded bg-indigo-100 text-indigo-800 flex items-center justify-center font-mono font-bold text-xs">
                      HTM
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-on-surface">Printable HTML Scorecard</p>
                      <p className="text-[10px] text-outline">Full interactive styling for desktop print</p>
                    </div>
                  </div>
                  <ExternalLink className="w-3.5 h-3.5 text-outline group-hover:text-secondary transition-colors" />
                </a>

                {/* CSV Requirements */}
                <a
                  href={csvReqsUrl}
                  download
                  className="p-3 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container transition-colors flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded bg-emerald-100 text-emerald-800 flex items-center justify-center font-mono font-bold text-xs">
                      CSV
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-on-surface">Requirements Dataset</p>
                      <p className="text-[10px] text-outline">Key, Statement, Classification, Scores</p>
                    </div>
                  </div>
                  <Download className="w-3.5 h-3.5 text-outline group-hover:text-secondary transition-colors" />
                </a>

                {/* CSV Issues */}
                <a
                  href={csvIssuesUrl}
                  download
                  className="p-3 rounded-lg border border-outline-variant/40 bg-surface-container-low hover:bg-surface-container transition-colors flex items-center justify-between group"
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-7 h-7 rounded bg-amber-100 text-amber-800 flex items-center justify-center font-mono font-bold text-xs">
                      CSV
                    </div>
                    <div>
                      <p className="text-xs font-semibold text-on-surface">Defect & Review Ledger</p>
                      <p className="text-[10px] text-outline">Rule IDs, Severity, Status, Review audit</p>
                    </div>
                  </div>
                  <Download className="w-3.5 h-3.5 text-outline group-hover:text-secondary transition-colors" />
                </a>
              </div>
            </div>
          </div>

          {/* ========================================================= */}
          {/* RIGHT PANEL: Live Interactive Document Preview (8 cols)   */}
          {/* ========================================================= */}
          <div className="lg:col-span-8 xl:col-span-8 flex flex-col bg-surface-container-lowest rounded-xl border border-outline-variant/60 shadow-xs overflow-hidden">
            {/* Preview Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 bg-surface-container-low/70 border-b border-outline-variant/50 text-xs">
              <div className="flex items-center gap-2">
                <FileCheck className="w-4 h-4 text-secondary" />
                <span className="font-semibold text-on-surface">
                  Live Audit Report Preview
                </span>
                <span className="text-[10px] font-mono text-outline">
                  {selectedDoc?.filename}
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setIframeKey((k) => k + 1)}
                  className="inline-flex items-center gap-1 text-[11px] text-outline hover:text-on-surface transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  <span>Reload</span>
                </button>

                <a
                  href={htmlReportUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] text-secondary hover:underline font-medium ml-2"
                >
                  <span>Open Fullscreen</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>

            {/* Embedded Live Preview */}
            <div className="w-full h-[640px] bg-slate-100 relative">
              {selectedDocId ? (
                <iframe
                  key={iframeKey}
                  src={htmlReportUrl}
                  title="Live Report Preview"
                  className="w-full h-full border-none"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-xs text-outline">
                  Select a document to preview report.
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<LoadingState message="Loading Reports Center..." className="py-20" />}>
      <ReportsPageContent />
    </Suspense>
  );
}
