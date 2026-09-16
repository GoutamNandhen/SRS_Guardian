import React from "react";
import { FileBarChart } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function ReportsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          Quality & Review Reports
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Download executive audit scorecards in HTML, CSV, and PDF formats.
        </p>
      </div>

      <EmptyState
        title="Report Center Active"
        description="The backend report generation service (Phase 9) is live! Export buttons for HTML, CSV, and PDF will be connected in Phase 11."
        icon={<FileBarChart className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
