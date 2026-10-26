"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FileText,
  ListOrdered,
  CheckSquare,
  Sparkles,
  GitCompare,
  FileCode2,
  FileBarChart,
  Settings,
  ShieldCheck,
  Building2,
  ChevronsUpDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
  badge?: string;
  badgeType?: "default" | "error" | "secondary";
}

const navItems: NavItem[] = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Documents", href: "/documents", icon: FileText },
  { name: "Requirement Viewer", href: "/requirements", icon: ListOrdered },
  { name: "Analysis", href: "/analysis", icon: CheckSquare },
  { name: "AI Suggestions", href: "/suggestions", icon: Sparkles },
  { name: "Version Comparison", href: "/compare", icon: GitCompare },
  { name: "Reports", href: "/reports", icon: FileBarChart },
  { name: "Traceability", href: "/traceability", icon: FileCode2 },
];

export function Sidebar() {
  const pathname = usePathname();
  const [organization, setOrganization] = useState<string>("SRS Guardian Workspace");

  useEffect(() => {
    let isMounted = true;
    api
      .getUserProfile()
      .then((data) => {
        if (isMounted && data.organization) {
          setOrganization(data.organization);
        }
      })
      .catch(() => {
        // Fallback silently if offline or uninitialized
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <aside className="fixed left-0 top-0 h-screen w-60 bg-surface-container-lowest border-r border-outline-variant/40 z-50 flex flex-col justify-between select-none">
      <div className="flex flex-col">
        {/* Logo & Brand Header */}
        <div className="h-12 px-3 border-b border-outline-variant/40 flex items-center justify-between">
          <div className="flex items-center gap-2 overflow-hidden">
            <div className="w-6 h-6 rounded bg-primary flex items-center justify-center text-primary-foreground flex-shrink-0">
              <ShieldCheck className="w-4 h-4" />
            </div>
            <span className="font-semibold text-sm text-on-surface tracking-tight truncate">
              SRS Guardian
            </span>
          </div>
          <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-surface-container text-on-surface-variant border border-outline-variant/60">
            v1.4
          </span>
        </div>

        {/* Workspace Selector */}
        <div className="p-2 border-b border-outline-variant/40">
          <Link
            href="/settings"
            title="Configure organization in Settings"
            className="px-2 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant/40 flex items-center justify-between cursor-pointer hover:bg-surface-container transition-colors"
          >
            <div className="flex items-center gap-2 overflow-hidden">
              <Building2 className="w-4 h-4 text-outline flex-shrink-0" />
              <div className="truncate">
                <p className="text-[10px] font-medium text-outline uppercase tracking-wider leading-none">
                  Workspace
                </p>
                <p className="text-xs font-medium text-on-surface truncate leading-tight mt-0.5">
                  {organization}
                </p>
              </div>
            </div>
            <ChevronsUpDown className="w-3.5 h-3.5 text-outline flex-shrink-0" />
          </Link>
        </div>

        {/* Navigation Items */}
        <nav className="flex flex-col gap-0.5 p-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors relative",
                  isActive
                    ? "bg-surface-container-high text-on-surface font-semibold before:absolute before:left-0 before:top-1.5 before:bottom-1.5 before:w-0.5 before:bg-secondary before:rounded-r"
                    : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
                )}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={cn("w-4 h-4", isActive ? "text-secondary" : "text-outline")} />
                  <span>{item.name}</span>
                </div>
                {item.badge && (
                  <span
                    className={cn(
                      "text-[10px] font-mono px-1.5 py-0.2 rounded border",
                      item.badgeType === "error"
                        ? "bg-error-container text-on-error-container border-error/20"
                        : item.badgeType === "secondary"
                        ? "bg-secondary-fixed text-on-secondary-fixed border-secondary/20"
                        : "bg-surface-container-low text-on-surface-variant border-outline-variant/40"
                    )}
                  >
                    {item.badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Navigation & Status */}
      <div className="flex flex-col border-t border-outline-variant/40 p-2 gap-1">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-colors",
            pathname === "/settings"
              ? "bg-surface-container-high text-on-surface font-semibold"
              : "text-on-surface-variant hover:bg-surface-container hover:text-on-surface"
          )}
        >
          <Settings className="w-4 h-4 text-outline" />
          <span>Settings</span>
        </Link>

        {/* Engine Status Indicator */}
        <div className="mt-1 px-2.5 py-1.5 rounded-lg bg-surface-container-low border border-outline-variant/40 flex items-center justify-between text-[11px]">
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="font-mono text-on-surface-variant">ISO 29148 Engine</span>
          </div>
          <span className="font-mono text-outline">Online</span>
        </div>
      </div>
    </aside>
  );
}
