import React from "react";
import { ListOrdered } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function RequirementsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          Requirement Viewer
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Inspect segmented requirements with inline ambiguity highlights, waterfall scoring, and SHAP token attributions.
        </p>
      </div>

      <EmptyState
        title="Requirement Viewer Foundation Active"
        description="Requirement Viewer feature page with interactive SHAP charts and inline problem spans will be completed in Phase 11."
        icon={<ListOrdered className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
