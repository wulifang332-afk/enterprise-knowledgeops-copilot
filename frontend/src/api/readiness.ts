import { getJson, postJson } from "./client";

export type AccessLevel = "public" | "internal" | "restricted" | "confidential";

export type PolicyType = "policy" | "sop" | "standard" | "guideline" | "form" | "manual";

export type SimulatedPersona = {
  persona_id: string;
  display_name: string;
  department: string;
  regions: string[];
  max_access_level: AccessLevel;
  allowed_policy_types: PolicyType[];
  description: string;
};

export type PersonaListResponse = {
  request_id: string;
  items: SimulatedPersona[];
};

export type ReadinessCapabilities = {
  access_policy_simulation: boolean;
  metadata_filter_generation: boolean;
  persona_explanations: boolean;
  local_first: boolean;
};

export type CorpusMetadataDistributions = {
  departments: Record<string, number>;
  regions: Record<string, number>;
  policy_types: Record<string, number>;
  owners: Record<string, number>;
  access_levels: Record<string, number>;
};

export type ReadinessGraphStatus = {
  available: boolean;
  node_count: number;
  edge_count: number;
};

export type ReadinessEvaluationStatus = {
  available: boolean;
  total_cases: number;
  passed_cases: number;
  pass_rate: number | null;
};

export type ReadinessGovernanceStatus = {
  available: boolean;
  feedback_count: number;
  review_status_breakdown: Record<string, number>;
};

export type ReadinessSummary = {
  request_id: string;
  simulation_only: true;
  personas_count: number;
  access_levels: AccessLevel[];
  readiness_capabilities: ReadinessCapabilities;
  corpus_metadata_distributions: CorpusMetadataDistributions;
  graph_status: ReadinessGraphStatus;
  evaluation_status: ReadinessEvaluationStatus;
  governance_status: ReadinessGovernanceStatus;
  non_goals: string[];
};

export type AccessPolicyAllowedFilters = {
  departments: string[];
  regions: string[];
  policy_types: string[];
  access_levels: AccessLevel[];
  owners: string[];
};

export type AccessPolicyRequest = {
  persona_id: string;
  requested_departments?: string[];
  requested_regions?: string[];
  requested_policy_types?: PolicyType[];
  requested_access_levels?: AccessLevel[];
  requested_owners?: string[];
};

export type AccessPolicyResponse = {
  request_id: string;
  persona: SimulatedPersona;
  allowed_filters: AccessPolicyAllowedFilters;
  denied_reasons: string[];
  explanation: string;
  simulation_only: true;
};

export function getReadinessSummary(): Promise<ReadinessSummary> {
  return getJson<ReadinessSummary>("/api/v1/readiness/summary");
}

export function getReadinessPersonas(): Promise<PersonaListResponse> {
  return getJson<PersonaListResponse>("/api/v1/readiness/personas");
}

export function simulateAccessPolicy(payload: AccessPolicyRequest): Promise<AccessPolicyResponse> {
  return postJson<AccessPolicyResponse, AccessPolicyRequest>("/api/v1/readiness/access-policy", payload);
}
