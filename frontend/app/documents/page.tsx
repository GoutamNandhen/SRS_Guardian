"use client";

import React, { useEffect, useState } from "react";
import { FileText, Upload, Plus } from "lucide-react";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import { ErrorState } from "@/components/ui/error-state";
import { api } from "@/services/api";
import { DocumentListItem } from "@/types";

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      setError(null);
      const docs = await api.getDocuments();
      setDocuments(docs);
    } catch (err: any) {
      setError(err.message || "Failed to load documents");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-outline-variant/30">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-on-surface">
            Document Repository
          </h1>
          <p className="text-xs text-on-surface-variant mt-0.5">
            Upload and manage Software Requirement Specification (SRS) source files.
          </p>
        </div>
        <button
          type="button"
          onClick={() => alert("Upload dialog will be enabled in Phase 11 feature page.")}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors shadow-sm"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>Upload Specification</span>
        </button>
      </div>

      {/* Content Area */}
      {loading ? (
        <LoadingState message="Loading documents from backend..." className="py-20" />
      ) : error ? (
        <ErrorState message={error} onRetry={fetchDocuments} className="my-8" />
      ) : documents.length === 0 ? (
        <EmptyState
          title="No specifications uploaded yet"
          description="Upload an SRS document in PDF, DOCX, or plain text format to begin automated requirement extraction."
          actionLabel="Upload Document"
          onAction={() => alert("Upload dialog will be enabled in Phase 11 feature page.")}
          icon={<FileText className="w-6 h-6 text-outline" />}
        />
      ) : (
        <div className="rounded-xl border border-outline-variant/40 bg-surface-container-lowest overflow-hidden shadow-sm">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-outline-variant/40 bg-surface-container-low/60 font-semibold text-outline">
                <th className="px-4 py-3">Document Name</th>
                <th className="px-4 py-3">Format</th>
                <th className="px-4 py-3">Requirements</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-outline-variant/30">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-surface-container-low/40 transition-colors">
                  <td className="px-4 py-3 font-medium text-on-surface flex items-center gap-2">
                    <FileText className="w-4 h-4 text-outline" />
                    <span>{doc.filename}</span>
                  </td>
                  <td className="px-4 py-3 uppercase font-mono text-[11px] text-on-surface-variant">
                    {doc.file_type}
                  </td>
                  <td className="px-4 py-3 font-mono text-on-surface">
                    {doc.requirements_count}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                      {doc.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-outline">
                    {new Date(doc.uploaded_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
