"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, CheckCircle2, FileCode2, FlaskConical, Loader2 } from "lucide-react";
import { api } from "@/services/api";
import type { DocumentListItem, Requirement } from "@/types";

type Preview = {
  supported: boolean; decision: string; reason?: string; threshold?: number;
  draft_cases?: Array<{ case_id: string; request: { amount: number } }>;
  oracle_assumption?: string;
};
type Observation = {
  case_id: string; request: { amount: number }; expected: { accepted: false };
  actual?: { accepted: boolean | null }; test_status: string; http_status?: number;
};
type Report = {
  demo_only: true; requirement_key: string; decision: string; cases: Observation[];
  target_revision: string; evidence_sha256: string; evidence_disclaimer: string;
};
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";
const example = "The banking system shall reject transfers exceeding ₹10,000.";

export default function VerificationPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [selectedDoc, setSelectedDoc] = useState("");
  const [requirements, setRequirements] = useState<Requirement[]>([]);
  const [reqKey, setReqKey] = useState("REQ-DEMO-001");
  const [text, setText] = useState(example);
  const [targetId, setTargetId] = useState<"demo_correct" | "demo_buggy">("demo_buggy");
  const [approved, setApproved] = useState(false);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getDocuments().then(setDocuments).catch(() => setDocuments([]));
  }, []);
  useEffect(() => {
    setRequirements([]);
    if (selectedDoc) api.getDocumentRequirements(Number(selectedDoc)).then(setRequirements).catch(() => setRequirements([]));
  }, [selectedDoc]);
  function reset() { setPreview(null); setReport(null); setApproved(false); }
  async function request<T>(path: string, body: Record<string, unknown>): Promise<T> {
    const response = await fetch(API_BASE + "/conformance/" + path, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Server request failed");
    return data as T;
  }
  async function runPreview() {
    setBusy(true); setError(""); setReport(null);
    try { setPreview(await request<Preview>("preview", { req_key: reqKey, requirement_text: text })); }
    catch (err) { setError(err instanceof Error ? err.message : "Could not preview"); }
    finally { setBusy(false); }
  }
  async function runDemo() {
    setBusy(true); setError(""); setReport(null);
    try {
      setReport(await request<Report>("demo/run", {
        req_key: reqKey, requirement_text: text, target_id: targetId, oracle_approved: approved,
      }));
    } catch (err) { setError(err instanceof Error ? err.message : "Could not run the demo"); }
    finally { setBusy(false); }
  }
  function downloadEvidence() {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "srs-guardian-m3-" + report.requirement_key + ".json";
    a.click(); URL.revokeObjectURL(url);
  }
  const box = "rounded-xl border border-outline-variant/50 bg-surface-container-lowest p-5 space-y-4";
  const input = "block w-full mt-1 p-2 bg-surface border border-outline-variant rounded-md text-sm";
  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">Executable Verification</h1>
        <p className="text-sm text-on-surface-variant mt-1">M3 — requirement-driven tests with actual response evidence.</p>
      </header>
      <div className="p-4 rounded-lg bg-surface-container-low border border-outline-variant/50 text-sm">
        <b>Trusted synthetic demo only.</b> This page does not execute uploaded repositories or verify matches from the{" "}
        <Link href="/traceability" className="underline">Traceability</Link> page. Passing tests does not prove full compliance.
      </div>
      <section className={box}>
        <h2 className="font-semibold flex items-center gap-2"><FileCode2 className="w-5 h-5" />1. Select a requirement</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <label className="text-sm">Existing document
            <select className={input} value={selectedDoc} onChange={e => setSelectedDoc(e.target.value)}>
              <option value="">Manual entry</option>
              {documents.map(d => <option key={d.id} value={d.id}>{d.filename}</option>)}
            </select>
          </label>
          <label className="text-sm">Extracted requirement
            <select className={input} defaultValue="" onChange={e => {
              const r = requirements.find(item => String(item.id) === e.target.value);
              if (r) { setReqKey(r.req_key); setText(r.text); reset(); }
            }}>
              <option value="">Select a requirement</option>
              {requirements.map(r => <option key={r.id} value={r.id}>{r.req_key}</option>)}
            </select>
          </label>
        </div>
        <label className="text-sm block">Requirement key
          <input className={input} maxLength={100} value={reqKey} onChange={e => { setReqKey(e.target.value); reset(); }} />
        </label>
        <label className="text-sm block">Requirement statement
          <textarea className={input + " min-h-24"} maxLength={1200} value={text} onChange={e => { setText(e.target.value); reset(); }} />
        </label>
        <button type="button" onClick={runPreview} disabled={busy || !text.trim()} className="px-4 py-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-50">
          Preview supported checks
        </button>
        {preview && <div className="p-3 bg-surface-container rounded-md space-y-2 text-sm">
          <b>{preview.supported ? "Supported numeric rule" : "Needs human clarification"}</b>
          {preview.reason && <p>{preview.reason}</p>}
          {preview.supported && <>
            <p>Threshold: ₹{preview.threshold?.toLocaleString("en-IN")}</p>
            <p>Forbidden transfer amounts: {preview.draft_cases?.map(c => "₹" + c.request.amount.toLocaleString("en-IN")).join(", ")}</p>
            <p className="text-on-surface-variant">{preview.oracle_assumption}</p>
          </>}
        </div>}
      </section>
      <section className={box}>
        <h2 className="font-semibold flex items-center gap-2"><FlaskConical className="w-5 h-5" />2. Run approved checks</h2>
        <label className="text-sm block">Installed demonstration target
          <select className={input} value={targetId} onChange={e => { setTargetId(e.target.value as "demo_buggy" | "demo_correct"); setReport(null); }}>
            <option value="demo_buggy">Deliberately faulty transfer API</option>
            <option value="demo_correct">Correct transfer API</option>
          </select>
        </label>
        <label className="flex gap-2 items-start text-sm">
          <input type="checkbox" className="mt-1" checked={approved} onChange={e => setApproved(e.target.checked)} />
          <span>I approve the test oracle: transfers above the stated threshold must return JSON with <code>accepted: false</code>. I understand that below-limit approval is not implied.</span>
        </label>
        <button type="button" onClick={runDemo} disabled={busy || !approved || !preview?.supported}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground flex gap-2 items-center disabled:opacity-50">
          {busy && <Loader2 className="w-4 h-4 animate-spin" />}Run trusted demo
        </button>
        {error && <p role="alert" className="text-error text-sm">{error}</p>}
      </section>
      {report && <section className={box}>
        <h2 className="font-semibold flex items-center gap-2">
          {report.decision === "observed_violation" ? <AlertTriangle className="w-5 h-5 text-error" /> : <CheckCircle2 className="w-5 h-5" />}
          3. Observed test evidence
        </h2>
        <p className="font-medium text-sm">{report.decision.replace(/_/g, " ")}</p>
        <div className="overflow-x-auto">
          <table className="text-sm w-full text-left"><thead><tr className="border-b">
            <th className="p-2">Case</th><th className="p-2">Input</th><th className="p-2">Expected</th>
            <th className="p-2">Observed accepted</th><th className="p-2">Result</th>
          </tr></thead><tbody>{report.cases.map(c => <tr className="border-b" key={c.case_id}>
            <td className="p-2">{c.case_id}</td><td className="p-2">₹{c.request.amount}</td>
            <td className="p-2">false</td><td className="p-2">{String(c.actual?.accepted)}</td><td className="p-2">{c.test_status}</td>
          </tr>)}</tbody></table>
        </div>
        <p className="text-xs text-on-surface-variant break-all">Evidence SHA-256: {report.evidence_sha256}</p>
        <p className="text-xs text-on-surface-variant">{report.evidence_disclaimer}</p>
        <button type="button" onClick={downloadEvidence} className="px-4 py-2 border rounded-lg text-sm">Download JSON evidence</button>
      </section>}
    </div>
  );
}
