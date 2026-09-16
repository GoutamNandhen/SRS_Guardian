import React from "react";
import { Sparkles } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";

export default function SuggestionsPage() {
  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      <div className="pb-2 border-b border-outline-variant/30">
        <h1 className="text-xl font-bold tracking-tight text-on-surface">
          AI Rewrite Suggestions
        </h1>
        <p className="text-xs text-on-surface-variant mt-0.5">
          Generative requirement rewriting with intent preservation and semantic similarity validation.
        </p>
      </div>

      <EmptyState
        title="AI Suggestions Module"
        description="LLM-based suggestion generator (Phase 14) will render suggestions here after model provider selection."
        icon={<Sparkles className="w-6 h-6 text-outline" />}
      />
    </div>
  );
}
