import { getJson } from "./client";

export type EvaluationMetrics = {
  pass_rate: number;
  intent_accuracy: number;
  route_accuracy: number;
  retrieval_hit_at_k: number | null;
  retrieval_recall_at_k: number | null;
  expected_chunk_presence_rate: number | null;
  answer_citation_non_empty_rate: number | null;
  citation_validity_rate: number | null;
  expected_citation_match_rate: number | null;
  grounded_answer_pass_rate: number | null;
  refusal_accuracy: number | null;
  out_of_scope_refusal_accuracy: number | null;
  unsupported_refusal_accuracy: number | null;
  insufficient_evidence_refusal_accuracy: number | null;
  fabricated_answer_rate: number | null;
};

export type SplitMetrics = {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number | null;
};

export type PerIntentMetrics = {
  total: number;
  passed: number;
  pass_rate: number;
  intent_accuracy: number;
};

export type EvaluationCaseResult = {
  case_id: string;
  split: string;
  query: string;
  passed: boolean;
  failed_checks: string[];
  retrieval_hit_at_k: boolean | null;
  retrieval_recall_at_k: number | null;
  citation_subset_valid: boolean | null;
  expected_citation_match: boolean | null;
  grounding_pass: boolean | null;
  refusal_correct: boolean | null;
  fabricated_answer: boolean;
};

export type EvaluationReport = {
  run_id: string;
  timestamp: string;
  dataset_version: string;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  metrics: EvaluationMetrics;
  split_metrics: Record<string, SplitMetrics>;
  per_intent_metrics: Record<string, PerIntentMetrics>;
  intent_confusion_summary: Record<string, Record<string, number>>;
  per_case_results: EvaluationCaseResult[];
  failures: EvaluationCaseResult[];
  limitations: string[];
};

export type EvaluationReportResponse = {
  request_id: string;
  report: EvaluationReport;
};

export type EvaluationCase = {
  case_id: string;
  split: string;
  query: string;
  top_k: number;
  generate_answer: boolean;
  include_graph: boolean;
  expected_intent: string;
  expected_route: string;
  expected_status: string;
  expected_answer_generation_status: string;
};

export type EvaluationCasesResponse = {
  request_id: string;
  dataset_version: string;
  total_cases: number;
  items: EvaluationCase[];
};

export function getEvaluationLatest(): Promise<EvaluationReportResponse> {
  return getJson<EvaluationReportResponse>("/api/v1/evaluation/latest");
}

export function getEvaluationCases(): Promise<EvaluationCasesResponse> {
  return getJson<EvaluationCasesResponse>("/api/v1/evaluation/cases");
}
