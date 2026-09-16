import React from "react";
import Link from "next/link";
import {
  FileText,
  ShieldCheck,
  AlertCircle,
  TrendingUp,
  ArrowRight,
  Sparkles,
  CheckCircle2,
} from "lucide-react";

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Top Header Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-outline-variant/30">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            Quality Assurance Dashboard
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Machine-assisted requirements verification adhering to ISO/IEC/IEEE 29148.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/documents"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-sm"
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Manage Documents</span>
          </Link>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/50 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-outline uppercase tracking-wider">
              Mean Quality Score
            </span>
            <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600">
              <TrendingUp className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold tracking-tight text-on-surface">82.5</div>
            <p className="text-[11px] text-emerald-600 font-medium mt-0.5">
              Acceptable quality grade
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/50 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-outline uppercase tracking-wider">
              Audited Requirements
            </span>
            <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold tracking-tight text-on-surface">6</div>
            <p className="text-[11px] text-on-surface-variant mt-0.5">
              100% automated rule coverage
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/50 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-outline uppercase tracking-wider">
              Flagged Issues
            </span>
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <AlertCircle className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold tracking-tight text-on-surface">6</div>
            <p className="text-[11px] text-amber-600 font-medium mt-0.5">
              Ambiguity & duplicate candidates
            </p>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-container-lowest border border-outline-variant/50 shadow-sm flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-outline uppercase tracking-wider">
              Human Review Status
            </span>
            <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600">
              <CheckCircle2 className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold tracking-tight text-on-surface">33.3%</div>
            <p className="text-[11px] text-indigo-600 font-medium mt-0.5">
              2 of 6 issues verified
            </p>
          </div>
        </div>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
        <Link
          href="/documents"
          className="group p-5 rounded-xl bg-surface-container-lowest border border-outline-variant/50 hover:border-secondary/40 transition-all shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center text-primary group-hover:bg-secondary-fixed group-hover:text-secondary transition-colors">
              <FileText className="w-5 h-5" />
            </div>
            <ArrowRight className="w-4 h-4 text-outline group-hover:text-secondary group-hover:translate-x-0.5 transition-all" />
          </div>
          <h3 className="text-sm font-semibold text-on-surface mt-4">Document Management</h3>
          <p className="text-xs text-on-surface-variant mt-1">
            Upload PDF, DOCX, or TXT specifications to extract requirements and trigger analysis.
          </p>
        </Link>

        <Link
          href="/requirements"
          className="group p-5 rounded-xl bg-surface-container-lowest border border-outline-variant/50 hover:border-secondary/40 transition-all shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center text-primary group-hover:bg-secondary-fixed group-hover:text-secondary transition-colors">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <ArrowRight className="w-4 h-4 text-outline group-hover:text-secondary group-hover:translate-x-0.5 transition-all" />
          </div>
          <h3 className="text-sm font-semibold text-on-surface mt-4">Requirement Viewer</h3>
          <p className="text-xs text-on-surface-variant mt-1">
            Inspect individual requirements with inline ambiguity spans, waterfall scoring, and SHAP explainability.
          </p>
        </Link>

        <Link
          href="/reports"
          className="group p-5 rounded-xl bg-surface-container-lowest border border-outline-variant/50 hover:border-secondary/40 transition-all shadow-sm"
        >
          <div className="flex items-center justify-between">
            <div className="w-9 h-9 rounded-lg bg-surface-container-low flex items-center justify-center text-primary group-hover:bg-secondary-fixed group-hover:text-secondary transition-colors">
              <Sparkles className="w-5 h-5" />
            </div>
            <ArrowRight className="w-4 h-4 text-outline group-hover:text-secondary group-hover:translate-x-0.5 transition-all" />
          </div>
          <h3 className="text-sm font-semibold text-on-surface mt-4">Report Generation</h3>
          <p className="text-xs text-on-surface-variant mt-1">
            Export printable audit reports, executive scorecards, and structured CSV files.
          </p>
        </Link>
      </div>
    </div>
  );
}
