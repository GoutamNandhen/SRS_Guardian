import React from "react";
import { Settings } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function SettingsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          System Settings & Verification Rules
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Configure rule thresholds, scoring weights, and ML model settings.
        </p>
      </div>

      <EmptyState
        title="Settings Module Active"
        description="Configuration panels for ISO 29148 check toggles, scoring weights, and embedding similarity thresholds will be connected here."
        icon={<Settings className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
