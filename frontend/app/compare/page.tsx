import React from "react";
import { GitCompare } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function ComparePage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          Version Comparison
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Side-by-side diffing and evolution tracking across SRS document revisions.
        </p>
      </div>

      <EmptyState
        title="Version Comparison Active"
        description="Unified diff toggle and requirement change tracking module will be connected in Phase 11."
        icon={<GitCompare className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
