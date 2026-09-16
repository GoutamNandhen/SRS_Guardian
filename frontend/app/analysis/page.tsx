import React from "react";
import { CheckSquare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function AnalysisPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          Quality Analysis & Issue Review
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Review potential ambiguity findings, semantic duplicate candidates, and readability metrics.
        </p>
      </div>

      <EmptyState
        title="Analysis Module Foundation Active"
        description="Categorized rule inspection and human review actions (Accept / Reject / Edit) will be connected in Phase 11."
        icon={<CheckSquare className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
