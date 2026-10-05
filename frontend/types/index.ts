/**
 * TypeScript type definitions mirroring SRS Guardian backend Pydantic schemas.
 */

export interface DocumentListItem {
  id: number;
  filename: string;
  file_type: string;
  file_size: number;
  page_count: number;
  status: "uploaded" | "extracted" | "analyzed" | "failed";
  uploaded_at: string;
  requirement_count: number;
  requirements_count?: number;
}

export interface DocumentDetail extends DocumentListItem {
  cleaned_text: string;
}

export interface ShapToken {
  token: string;
  shap_value: number;
}

export interface Requirement {
  id: number;
  document_id: number;
  req_key: string;
  text: string;
  source_layer: string;
  confidence: number;
  char_start: number;
  char_end: number;
  section: string | null;
  classification_label: "Functional" | "Non-Functional" | null;
  classification_prob: number | null;
  classification_explanation: ShapToken[] | string | null;
  created_at: string;
}

export interface SubScores {
  clarity: number;
  ambiguity: number;
  testability: number;
  readability: number;
  structure: number;
  consistency: number;
}

export interface WaterfallStep {
  step_number: number;
  step_name: string;
  rule_id: string;
  deduction: number;
  current_score: number;
  explanation: string;
}

export interface PenaltyApplied {
  rule_id: string;
  name: string;
  deduction: number;
  matched_text?: string | null;
}

export interface Review {
  id: number;
  issue_id: number;
  action: "accept" | "reject" | "edit" | "mark_reviewed";
  edited_text?: string | null;
  note?: string | null;
  reviewed_at: string;
}

export interface Issue {
  id: number;
  requirement_id: number;
  req_key?: string | null;
  module: string;
  type: string;
  severity: "info" | "warning" | "error";
  explanation: string | Record<string, any>;
  status: "ai_flagged" | "accepted" | "rejected" | "reviewed" | "edited";
  is_human_reviewed: boolean;
  created_at: string;
  reviews: Review[];
}

export interface RequirementDetail extends Requirement {
  quality_score?: number;
  sub_scores?: SubScores;
  waterfall?: WaterfallStep[];
  issues: Issue[];
  ears_result?: EarsResult | null;
  iso_checks?: IsoCheckItem[] | null;
}

export interface EarsResult {
  pattern: string;
  is_valid_ears: boolean;
  trigger?: string | null;
  state?: string | null;
  feature?: string | null;
  condition?: string | null;
  system?: string | null;
  modal?: string | null;
  response?: string | null;
  missing_elements: string[];
  explanation: string;
  suggestion?: string | null;
  matched_template?: string | null;
}

export interface IsoCheckItem {
  check_id: string;
  characteristic: string;
  status: "passed" | "warning" | "failed";
  score_deduction: number;
  explanation: string;
  suggestion?: string | null;
  spans?: Array<{ start: number; end: number; text: string }>;
}

export interface RequirementIsoReport {
  requirement_id?: number | null;
  req_key: string;
  text: string;
  ears_result: EarsResult;
  checks: IsoCheckItem[];
  total_iso_deductions: number;
  conformance_summary: string;
}

export interface DocumentStandardsResponse {
  document_id: number;
  total_requirements: number;
  standards_name: string;
  fully_conforming_count: number;
  warning_count: number;
  failed_count: number;
  requirements: RequirementIsoReport[];
}


export interface WorstRequirementItem {
  requirement_id: number;
  req_key: string;
  overall_score: number;
  issues_count: number;
  text: string;
}

export interface ScoreDistribution {
  "90-100": number;
  "70-89": number;
  "50-69": number;
  "<50": number;
}

export interface DocumentQualitySummary {
  document_id: number;
  total_requirements: number;
  mean_score: number;
  median_score: number;
  min_score: number;
  max_score: number;
  distribution: ScoreDistribution;
  worst_requirements: WorstRequirementItem[];
  issue_counts: Record<string, number>;
  requirements: RequirementDetail[];
}

export interface DocumentAnalysisResponse {
  document_id: number;
  status: string;
  requirements_count: number;
  issues_count: number;
  quality_summary: DocumentQualitySummary;
}

export interface ReviewActionRequest {
  action: "accept" | "reject" | "edit" | "mark_reviewed";
  edited_text?: string | null;
  note?: string | null;
}

export interface AlignedPhrase {
  phrase_1: { text: string; start: number; end: number };
  phrase_2: { text: string; start: number; end: number };
  similarity: number;
}

export interface DuplicatePair {
  requirement_id_1: number;
  req_key_1: string;
  text_1: string;
  requirement_id_2: number;
  req_key_2: string;
  text_2: string;
  similarity_score: number;
  aligned_phrases: AlignedPhrase[];
  explanation: Record<string, any>;
}

export interface DocumentDuplicatesResponse {
  document_id: number;
  threshold: number;
  total_pairs_checked: number;
  duplicate_pairs_count: number;
  duplicates: DuplicatePair[];
}

export interface ContradictionConstraint {
  entity: string;
  attribute: string;
  comparator: string;
  value: number;
  value_max?: number | null;
  unit: string;
  range_display: string;
  raw_span?: string;
}

export interface ContradictionItem {
  finding_id: string;
  issue_id?: number | null;
  mechanism: "numeric" | "semantic";
  rule_id: string;
  severity: "critical" | "warning" | "info";
  confidence: number;
  requirement_id_1?: number | null;
  req_key_1: string;
  text_1: string;
  constraint_1?: ContradictionConstraint | null;
  requirement_id_2?: number | null;
  req_key_2: string;
  text_2: string;
  constraint_2?: ContradictionConstraint | null;
  human_explanation: string;
  suggestion: string;
  status: "ai_flagged" | "accepted" | "rejected" | "reviewed" | "edited";
}

export interface DocumentContradictionsResponse {
  document_id: number;
  total_contradictions_count: number;
  numeric_conflicts_count: number;
  semantic_contradictions_count: number;
  contradictions: ContradictionItem[];
}

export interface ContradictionExplainResponse {
  issue_id: number;
  finding_id: string;
  tokens: { token: string; attribution: number }[];
}

export interface RewriteSuggestionResponse {
  enabled: boolean;
  cached: boolean;
  original_text: string;
  suggested_text?: string | null;
  rationale?: string | null;
  changes_made: string[];
  conforms_to_ears: boolean;
  error?: string | null;
}

export interface GherkinGenerationResponse {
  enabled: boolean;
  cached: boolean;
  source?: "ears_rule" | "llm" | "fallback_rule" | string | null;
  ears_pattern?: string | null;
  requirement_id?: number | null;
  requirement_text: string;
  gherkin_scenarios?: string | null;
  error?: string | null;
}

export interface ClusteredRequirementItem {
  id: number;
  req_key: string;
  text: string;
  classification_label?: string | null;
  section?: string | null;
}

export interface ClusterGroup {
  cluster_id: number;
  label: string;
  keywords: string[];
  size: number;
  requirements: ClusteredRequirementItem[];
}

export interface DocumentClustersResponse {
  document_id: number;
  total_requirements: number;
  num_clusters: number;
  clusters: ClusterGroup[];
}

export interface IssueDiffItem {
  rule_id: string;
  severity: "critical" | "warning" | "info";
  human_explanation: string;
}

export interface RequirementComparisonItem {
  status: "added" | "removed" | "modified" | "unchanged";
  req_key: string;
  text_v1?: string | null;
  text_v2?: string | null;
  score_v1?: number | null;
  score_v2?: number | null;
  score_delta?: number | null;
  similarity?: number | null;
  diff_text?: string | null;
  resolved_issues: IssueDiffItem[];
  new_issues: IssueDiffItem[];
  persistent_issues: IssueDiffItem[];
}

export interface DocumentComparisonResponse {
  doc1_id: number;
  doc1_filename: string;
  doc2_id: number;
  doc2_filename: string;
  total_v1: number;
  total_v2: number;
  added_count: number;
  removed_count: number;
  modified_count: number;
  unchanged_count: number;
  avg_score_v1: number;
  avg_score_v2: number;
  score_delta: number;
  total_resolved_issues: number;
  total_new_issues: number;
  items: RequirementComparisonItem[];
}

export interface FindingSpan {
  start: number;
  end: number;
  text: string;
  weight: number;
}

export interface AnnotatedFinding {
  finding_id: string;
  issue_id?: number | null;
  requirement_id: number;
  req_key: string;
  module: string;
  type: string;
  severity: "info" | "warning" | "critical";
  confidence: number | null;
  confidence_band: "high" | "medium" | "low" | "unavailable";
  source_text: string;
  spans: FindingSpan[];
  has_sub_spans: boolean;
  human_explanation: string;
  suggestion?: string | null;
  rule_provenance: string;
  status: "ai_flagged" | "accepted" | "rejected" | "reviewed" | "edited";
  is_pair_finding: boolean;
  target_requirement_id?: number | null;
  target_req_key?: string | null;
  metadata?: Record<string, any>;
}

export interface RequirementReviewItem {
  requirement_id: number;
  req_key: string;
  text: string;
  char_start: number;
  char_end: number;
  section?: string | null;
  source_layer: string;
  confidence: number;
  classification_label?: string | null;
  classification_prob?: number | null;
  quality_score: number;
  sub_scores: Record<string, number>;
  waterfall_steps: any[];
  ears_pattern?: string | null;
  is_valid_ears?: boolean | null;
  findings: AnnotatedFinding[];
  ai_rewrite?: any | null;
  gherkin_scenario?: string | null;
  review_status: string;
}

export interface ExecutiveReviewRow {
  requirement: string;
  status: "CRITICAL" | "WARNING" | "OK";
  finding: string;
  suggested_action: string;
  problem_phrase?: string | null;
  short_reason?: string | null;
  is_pair: boolean;
  req_ids: number[];
  confidence?: number | null;
  confidence_band: "high" | "medium" | "low" | "unavailable";
  text_snippet?: string | null;
}

export interface ShapFeatureItem {
  token: string;
  shap_value: number;
  direction: "positive" | "negative";
}

export interface ShapRequirementAttribution {
  requirement_id: number;
  req_key: string;
  text: string;
  predicted_class: string;
  probability: number;
  top_features: ShapFeatureItem[];
  human_interpretation: string;
}

export interface DocumentReviewReport {
  document_id: number;
  filename: string;
  file_type: string;
  page_count: number;
  uploaded_at: string;
  status: string;
  cleaned_text: string;
  raw_text?: string | null;
  total_requirements: number;
  total_findings: number;
  overall_status?: "NEEDS ATTENTION" | "PASSED WITH WARNINGS" | "ACCEPTABLE" | string;
  quality_summary: any;
  findings_by_severity: Record<string, number>;
  findings_by_module: Record<string, number>;
  findings_by_confidence: Record<string, number>;
  executive_summary_table?: ExecutiveReviewRow[];
  requirements: RequirementReviewItem[];
  all_findings: AnnotatedFinding[];
  system_evaluation?: any | null;
  shap_attributions?: ShapRequirementAttribution[];
  dynamic_conclusion?: string | null;
}




