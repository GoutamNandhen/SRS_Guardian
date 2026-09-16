import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({
  message = "Loading data...",
  className,
}: LoadingStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center p-8 text-center text-on-surface-variant",
        className
      )}
    >
      <Loader2 className="h-6 w-6 animate-spin text-secondary mb-3" />
      <p className="text-sm font-medium text-on-surface-variant">{message}</p>
    </div>
  );
}
