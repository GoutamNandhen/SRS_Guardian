"use client";

import React, { useEffect, useState } from "react";
import {
  User,
  Building,
  Mail,
  Briefcase,
  Phone,
  Save,
  RotateCcw,
  CheckCircle2,
  AlertCircle,
  Sliders,
  ShieldCheck,
  FileCheck,
} from "lucide-react";
import { api } from "@/services/api";
import { UserProfile } from "@/types";

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile>({
    full_name: "",
    email: "",
    organization: "",
    role: "",
    phone: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Load existing profile from backend on mount
  const loadProfile = async () => {
    try {
      setLoading(true);
      setSaveError(null);
      const data = await api.getUserProfile();
      setProfile({
        full_name: data.full_name || "",
        email: data.email || "",
        organization: data.organization || "",
        role: data.role || "",
        phone: data.phone || "",
        updated_at: data.updated_at,
      });
    } catch (err: any) {
      setSaveError(err.message || "Failed to load user profile");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSaving(true);
      setSaveError(null);
      setSaveSuccess(false);

      const updated = await api.updateUserProfile({
        full_name: profile.full_name?.trim() || null,
        email: profile.email?.trim() || null,
        organization: profile.organization?.trim() || null,
        role: profile.role?.trim() || null,
        phone: profile.phone?.trim() || null,
      });

      setProfile({
        full_name: updated.full_name || "",
        email: updated.email || "",
        organization: updated.organization || "",
        role: updated.role || "",
        phone: updated.phone || "",
        updated_at: updated.updated_at,
      });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 4000);
    } catch (err: any) {
      setSaveError(err.message || "Failed to save profile changes");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div className="pb-3 border-b border-outline-variant/40 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            Settings & Personal Details
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Configure reviewer identity for audit logs, reports, and system inspection rules.
          </p>
        </div>
        {profile.updated_at && (
          <span className="text-[11px] font-mono text-outline">
            Last updated: {new Date(profile.updated_at).toLocaleString()}
          </span>
        )}
      </div>

      {/* Notifications */}
      {saveSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs flex items-center gap-2.5 shadow-xs">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span className="font-medium">
            Personal details saved successfully. New review reports will reflect these details.
          </span>
        </div>
      )}

      {saveError && (
        <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-300 text-rose-900 text-xs flex items-center gap-2.5 shadow-xs">
          <AlertCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
          <span className="font-medium">{saveError}</span>
        </div>
      )}

      {/* Section 1: Personal Details */}
      <div className="rounded-2xl border border-outline-variant/50 bg-surface shadow-xs overflow-hidden">
        <div className="p-5 border-b border-outline-variant/40 bg-surface-container-low/40 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
              <User className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-on-surface">Reviewer Personal Details</h2>
              <p className="text-[11px] text-outline">
                Authoritative personal identity used in formal review reports, PDF exports, and sign-off blocks.
              </p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSave} className="p-6 flex flex-col gap-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            {/* Full Name */}
            <div>
              <label className="text-xs font-semibold text-on-surface block mb-1.5 flex items-center gap-1.5">
                <User className="w-3.5 h-3.5 text-outline" />
                <span>Full Name</span>
              </label>
              <input
                type="text"
                disabled={loading}
                value={profile.full_name || ""}
                onChange={(e) => setProfile({ ...profile, full_name: e.target.value })}
                placeholder="e.g. Jane Smith"
                className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              />
              <span className="text-[10px] text-outline mt-1 block">
                Leave empty to display &quot;Not provided&quot; in reports.
              </span>
            </div>

            {/* Email */}
            <div>
              <label className="text-xs font-semibold text-on-surface block mb-1.5 flex items-center gap-1.5">
                <Mail className="w-3.5 h-3.5 text-outline" />
                <span>Email Address</span>
              </label>
              <input
                type="email"
                disabled={loading}
                value={profile.email || ""}
                onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                placeholder="e.g. reviewer@institution.org"
                className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              />
            </div>

            {/* Organization */}
            <div>
              <label className="text-xs font-semibold text-on-surface block mb-1.5 flex items-center gap-1.5">
                <Building className="w-3.5 h-3.5 text-outline" />
                <span>Organization / Institution</span>
              </label>
              <input
                type="text"
                disabled={loading}
                value={profile.organization || ""}
                onChange={(e) => setProfile({ ...profile, organization: e.target.value })}
                placeholder="e.g. Department of Computer Science & Engineering"
                className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              />
            </div>

            {/* Role */}
            <div>
              <label className="text-xs font-semibold text-on-surface block mb-1.5 flex items-center gap-1.5">
                <Briefcase className="w-3.5 h-3.5 text-outline" />
                <span>Professional Role / Title</span>
              </label>
              <input
                type="text"
                disabled={loading}
                value={profile.role || ""}
                onChange={(e) => setProfile({ ...profile, role: e.target.value })}
                placeholder="e.g. Requirements Engineer / Systems Architect"
                className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              />
            </div>

            {/* Phone */}
            <div>
              <label className="text-xs font-semibold text-on-surface block mb-1.5 flex items-center gap-1.5">
                <Phone className="w-3.5 h-3.5 text-outline" />
                <span>Contact Phone (Optional)</span>
              </label>
              <input
                type="tel"
                disabled={loading}
                value={profile.phone || ""}
                onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                placeholder="e.g. +1 555-0199"
                className="w-full text-xs p-2.5 rounded-lg bg-surface-container-lowest border border-outline-variant/60 text-on-surface focus:outline-none focus:ring-1 focus:ring-primary focus:border-primary disabled:opacity-50"
              />
            </div>
          </div>

          <div className="pt-3 border-t border-outline-variant/40 flex items-center justify-between">
            <span className="text-[11px] text-outline">
              Changes are immediately synchronized to the authoritative profile database.
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={loadProfile}
                disabled={loading || saving}
                className="px-3 py-2 rounded-lg bg-surface-container border border-outline-variant/60 text-xs font-medium text-on-surface hover:bg-surface-container-high transition-colors flex items-center gap-1.5 disabled:opacity-50"
              >
                <RotateCcw className="w-3.5 h-3.5 text-outline" />
                <span>Reload</span>
              </button>
              <button
                type="submit"
                disabled={loading || saving}
                className="px-4 py-2 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shadow-xs flex items-center gap-1.5 disabled:opacity-50"
              >
                <Save className="w-3.5 h-3.5" />
                <span>{saving ? "Saving..." : "Save Personal Details"}</span>
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Section 2: Rule Engine Overview (Read-Only) */}
      <div className="rounded-2xl border border-outline-variant/50 bg-surface shadow-xs overflow-hidden">
        <div className="p-5 border-b border-outline-variant/40 bg-surface-container-low/40 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-secondary/10 flex items-center justify-center text-secondary">
              <Sliders className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-on-surface">Inspection Engines & Verification Weights</h2>
              <p className="text-[11px] text-outline">
                Selected machine-checkable checks based on ISO/IEC/IEEE 29148 standards and EARS syntax.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl border border-outline-variant/40 bg-surface-container-lowest flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span>Ambiguity Engine</span>
            </div>
            <p className="text-[11px] text-outline">
              6 deterministic rule checks: weak terms, weak modals, missing metrics, vague pronouns, compound clauses, passive voice without actor.
            </p>
            <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200 w-fit mt-1">
              Active • Max deduction -15.0/check
            </span>
          </div>

          <div className="p-4 rounded-xl border border-outline-variant/40 bg-surface-container-lowest flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <FileCheck className="w-4 h-4 text-indigo-600" />
              <span>Contradiction Engine</span>
            </div>
            <p className="text-[11px] text-outline">
              Dual mechanism: deterministic numeric interval conflict checking $[low_1, high_1] \cap [low_2, high_2] = \emptyset$ and NLI semantic contradiction.
            </p>
            <span className="text-[10px] font-mono text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200 w-fit mt-1">
              Active • Penalty -25.0
            </span>
          </div>

          <div className="p-4 rounded-xl border border-outline-variant/40 bg-surface-container-lowest flex flex-col gap-1.5">
            <div className="flex items-center gap-2 text-xs font-bold text-on-surface">
              <Sliders className="w-4 h-4 text-amber-600" />
              <span>EARS & ISO 29148</span>
            </div>
            <p className="text-[11px] text-outline">
              Validates 6 EARS templates (Ubiquitous, Event-driven, State-driven, Unwanted, Optional, Complex) and 7 quality characteristics.
            </p>
            <span className="text-[10px] font-mono text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 w-fit mt-1">
              Active • Evaluated per requirement
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
