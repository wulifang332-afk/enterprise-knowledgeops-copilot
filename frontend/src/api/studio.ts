import { getJson } from "./client";

export type WorkspaceSummary = {
  documents: number;
  chunks: number;
  graph_nodes: number;
  graph_edges: number;
};

export type EvaluationSummary = {
  available: boolean;
  run_id: string | null;
  timestamp: string | null;
  dataset_version: string | null;
  total_cases: number;
  passed_cases: number;
  failed_cases: number;
  pass_rate: number | null;
  intent_accuracy: number | null;
  route_accuracy: number | null;
  citation_validity_rate: number | null;
  grounded_answer_pass_rate: number | null;
  refusal_accuracy: number | null;
  fabricated_answer_rate: number | null;
  core_total: number;
  core_passed: number;
  holdout_total: number;
  holdout_passed: number;
};

export function getWorkspaceSummary(): Promise<WorkspaceSummary> {
  return getJson<WorkspaceSummary>("/api/v1/workspace/summary");
}

export function getEvaluationSummary(): Promise<EvaluationSummary> {
  return getJson<EvaluationSummary>("/api/v1/evaluation/summary");
}
