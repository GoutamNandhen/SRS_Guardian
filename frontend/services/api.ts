/**
 * SRS Guardian — Typed Frontend API Client
 * Centralized service with one function per backend endpoint.
 */

import {
  DocumentListItem,
  DocumentDetail,
  Requirement,
  RequirementDetail,
  DocumentQualitySummary,
  DocumentAnalysisResponse,
  DocumentDuplicatesResponse,
  DocumentContradictionsResponse,
  ContradictionExplainResponse,
  DocumentStandardsResponse,
  Issue,
  ReviewActionRequest,
  RewriteSuggestionResponse,
  GherkinGenerationResponse,
  DocumentClustersResponse,
  DocumentComparisonResponse,
  DocumentReviewReport,
  UserProfile,
} from "../types";


const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {};
  if (options?.body) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // Ignore JSON parse failure on non-JSON response
    }
    throw new ApiError(errorDetail, res.status);
  }

  return res.json();
}

export const api = {
  // --- Documents ---
  async getDocuments(): Promise<DocumentListItem[]> {
    return fetchJson<DocumentListItem[]>(`${API_BASE}/documents`);
  },

  async getDocument(id: number): Promise<DocumentDetail> {
    return fetchJson<DocumentDetail>(`${API_BASE}/documents/${id}`);
  },

  async uploadDocument(file: File): Promise<DocumentListItem> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new ApiError(err.detail || "Upload failed", res.status);
    }

    return res.json();
  },

  async deleteDocument(id: number): Promise<{ message: string }> {
    return fetchJson<{ message: string }>(`${API_BASE}/documents/${id}`, {
      method: "DELETE",
    });
  },

  // --- Requirements ---
  async extractRequirements(documentId: number): Promise<{ message: string; requirements_count: number }> {
    return fetchJson(`${API_BASE}/documents/${documentId}/extract`, {
      method: "POST",
    });
  },

  async getDocumentRequirements(documentId: number): Promise<Requirement[]> {
    return fetchJson<Requirement[]>(`${API_BASE}/documents/${documentId}/requirements`);
  },

  async getRequirement(id: number): Promise<RequirementDetail> {
    return fetchJson<RequirementDetail>(`${API_BASE}/requirements/${id}`);
  },

  // --- Analysis & Quality ---
  async analyzeDocument(documentId: number): Promise<DocumentAnalysisResponse> {
    return fetchJson<DocumentAnalysisResponse>(`${API_BASE}/documents/${documentId}/analyze`, {
      method: "POST",
    });
  },

  async getDocumentQuality(documentId: number): Promise<DocumentQualitySummary> {
    return fetchJson<DocumentQualitySummary>(`${API_BASE}/documents/${documentId}/quality`);
  },

  async getDocumentDuplicates(documentId: number, threshold?: number): Promise<DocumentDuplicatesResponse> {
    const url = threshold !== undefined
      ? `${API_BASE}/documents/${documentId}/duplicates?threshold=${threshold}`
      : `${API_BASE}/documents/${documentId}/duplicates`;
    return fetchJson<DocumentDuplicatesResponse>(url);
  },

  async getDocumentIssues(
    documentId: number,
    params?: { module?: string; severity?: string; status_filter?: string }
  ): Promise<Issue[]> {
    const query = new URLSearchParams();
    if (params?.module) query.set("module", params.module);
    if (params?.severity) query.set("severity", params.severity);
    if (params?.status_filter) query.set("status_filter", params.status_filter);

    const qs = query.toString();
    const url = qs ? `${API_BASE}/documents/${documentId}/issues?${qs}` : `${API_BASE}/documents/${documentId}/issues`;
    return fetchJson<Issue[]>(url);
  },

  async getDocumentContradictions(documentId: number): Promise<DocumentContradictionsResponse> {
    return fetchJson<DocumentContradictionsResponse>(`${API_BASE}/documents/${documentId}/contradictions`);
  },

  async explainContradiction(issueId: number): Promise<ContradictionExplainResponse> {
    return fetchJson<ContradictionExplainResponse>(`${API_BASE}/contradictions/${issueId}/explain`);
  },

  async getDocumentStandards(documentId: number): Promise<DocumentStandardsResponse> {
    return fetchJson<DocumentStandardsResponse>(`${API_BASE}/documents/${documentId}/standards`);
  },


  // --- Human Review ---
  async reviewIssue(issueId: number, actionData: ReviewActionRequest): Promise<Issue> {
    return fetchJson<Issue>(`${API_BASE}/issues/${issueId}/review`, {
      method: "POST",
      body: JSON.stringify(actionData),
    });
  },

  // --- AI Assistance (Tier 2 - Phase 14) ---
  async suggestRewrite(requirementId: number): Promise<RewriteSuggestionResponse> {
    return fetchJson<RewriteSuggestionResponse>(`${API_BASE}/requirements/${requirementId}/suggest-rewrite`, {
      method: "POST",
    });
  },

  async generateGherkin(requirementId: number): Promise<GherkinGenerationResponse> {
    return fetchJson<GherkinGenerationResponse>(`${API_BASE}/requirements/${requirementId}/generate-gherkin`, {
      method: "POST",
    });
  },

  // --- Thematic Clustering (Tier 3 - Phase 15B) ---
  async getDocumentClusters(documentId: number, k?: number): Promise<DocumentClustersResponse> {
    const query = k ? `?k=${k}` : "";
    return fetchJson<DocumentClustersResponse>(`${API_BASE}/documents/${documentId}/clusters${query}`);
  },

  // --- Version Comparison (Tier 3 - Phase 15C) ---
  async compareDocuments(documentId1: number, documentId2: number): Promise<DocumentComparisonResponse> {
    return fetchJson<DocumentComparisonResponse>(`${API_BASE}/documents/${documentId1}/compare/${documentId2}`);
  },

  // --- Reports Export URLs ---
  getReportUrl(documentId: number, format: "html" | "csv" | "pdf", type: "requirements" | "issues" = "requirements"): string {
    return `${API_BASE}/documents/${documentId}/report?format=${format}&type=${type}`;
  },

  // --- Phase 18: Explainable Review & Comprehensive Reporting ---
  async getReviewReport(documentId: number): Promise<DocumentReviewReport> {
    return fetchJson<DocumentReviewReport>(`${API_BASE}/documents/${documentId}/review-report`);
  },

  getAnnotatedPdfUrl(documentId: number): string {
    return `${API_BASE}/documents/${documentId}/review-report/annotated-pdf`;
  },

  getComprehensivePdfUrl(documentId: number): string {
    return `${API_BASE}/documents/${documentId}/review-report/pdf`;
  },

  getComprehensiveDocxUrl(documentId: number): string {
    return `${API_BASE}/documents/${documentId}/review-report/docx`;
  },

  // --- Phase 18.2: User Profile ---
  async getUserProfile(): Promise<UserProfile> {
    return fetchJson<UserProfile>(`${API_BASE}/profile`);
  },

  async updateUserProfile(profile: Partial<UserProfile>): Promise<UserProfile> {
    return fetchJson<UserProfile>(`${API_BASE}/profile`, {
      method: "PUT",
      body: JSON.stringify(profile),
    });
  },
};

