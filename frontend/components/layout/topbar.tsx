"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import {
  Search,
  Sun,
  Moon,
  User,
} from "lucide-react";
import { api } from "@/services/api";
import { UserProfile } from "@/types";

export function Topbar() {
  const [isDark, setIsDark] = useState(false);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    let isMounted = true;
    api
      .getUserProfile()
      .then((data) => {
        if (isMounted) setProfile(data);
      })
      .catch(() => {
        // Fallback silently if offline or uninitialized
      });
    return () => {
      isMounted = false;
    };
  }, []);

  const toggleTheme = () => {
    setIsDark(!isDark);
    if (!isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  };

  const displayName = profile?.full_name || "Reviewer";
  const displayRole = profile?.role || "Requirements Engineer";

  return (
    <header className="fixed top-0 left-60 right-0 h-12 bg-surface-container-lowest border-b border-outline-variant/40 z-40 flex items-center justify-between px-6 select-none">
      {/* Breadcrumbs */}
      <div className="flex items-center gap-2 text-xs text-on-surface-variant">
        <div className="flex items-center gap-1.5 font-medium">
          <span className="hover:text-on-surface cursor-pointer">SRS Guardian</span>
          <span className="text-outline">/</span>
          <span className="hover:text-on-surface cursor-pointer">Projects</span>
          <span className="text-outline">/</span>
          <span className="text-on-surface font-semibold">Workspace</span>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Global Search Bar */}
        <div className="flex items-center gap-2 w-64 h-8 px-2.5 rounded-lg bg-surface-container-low border border-outline-variant/60 focus-within:border-secondary transition-all">
          <Search className="w-3.5 h-3.5 text-outline flex-shrink-0" />
          <input
            type="text"
            placeholder="Search rules, requirements..."
            className="w-full bg-transparent border-none outline-none text-xs text-on-surface placeholder:text-outline"
          />
          <span className="text-[10px] font-mono px-1 py-0.2 rounded bg-surface-container-lowest text-outline border border-outline-variant/60">
            ⌘K
          </span>
        </div>

        <div className="h-4 w-px bg-outline-variant/50" />

        {/* Sync Status Badge */}
        <div className="flex items-center gap-1.5 px-2 py-1 rounded bg-surface-container-low text-[11px] text-on-surface-variant border border-outline-variant/40">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span>Backend Connected</span>
        </div>

        {/* Theme Switcher */}
        <button
          type="button"
          onClick={toggleTheme}
          aria-label="Toggle Theme"
          className="p-1.5 text-on-surface-variant hover:text-on-surface hover:bg-surface-container rounded-lg transition-colors"
        >
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        {/* User Chip */}
        <Link
          href="/settings"
          title="Manage reviewer profile in Settings"
          className="flex items-center gap-2 pl-1 border-l border-outline-variant/40 hover:opacity-80 transition-opacity"
        >
          <div className="w-7 h-7 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-semibold">
            <User className="w-3.5 h-3.5" />
          </div>
          <div className="hidden lg:flex flex-col text-left text-xs">
            <span className="font-medium text-on-surface leading-tight">
              {displayName}
            </span>
            <span className="text-[10px] text-outline leading-tight">
              {displayRole}
            </span>
          </div>
        </Link>
      </div>
    </header>
  );
}
