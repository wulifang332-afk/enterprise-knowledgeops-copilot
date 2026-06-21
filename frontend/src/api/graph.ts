import { getJson } from "./client";

export type NodeType =
  | "Policy"
  | "SOP"
  | "Document"
  | "Department"
  | "Region"
  | "Role"
  | "System"
  | "Form"
  | "ApprovalLevel"
  | "RiskType"
  | "DataType"
  | "Process"
  | "Threshold"
  | "TimeRequirement"
  | "Vendor"
  | "Customer"
  | "IncidentSeverity"
  | "AccessLevel";

export type RelationType =
  | "REQUIRES"
  | "APPROVES"
  | "OWNS"
  | "APPLIES_TO"
  | "ESCALATES_TO"
  | "USES_SYSTEM"
  | "HAS_THRESHOLD"
  | "HAS_TIME_REQUIREMENT"
  | "HAS_ACCESS_LEVEL"
  | "RELATED_TO"
  | "GOVERNS"
  | "MENTIONS";

export type KnowledgeGraphNode = {
  node_id: string;
  label: string;
  type: NodeType;
  source_doc_ids: string[];
  source_chunk_ids: string[];
  mentions: string[];
  confidence: number;
  created_by: string;
};

export type KnowledgeGraphEdge = {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  relation_type: RelationType;
  source_doc_id: string;
  source_chunk_id: string;
  evidence_quote: string;
  confidence: number;
  created_by: string;
};

export type GraphNodeListResponse = {
  request_id: string;
  total: number;
  offset: number;
  limit: number;
  items: KnowledgeGraphNode[];
};

export type GraphEdgeListResponse = {
  request_id: string;
  total: number;
  offset: number;
  limit: number;
  items: KnowledgeGraphEdge[];
};

export type GraphNeighborhoodResponse = {
  request_id: string;
  node_id: string;
  depth: number;
  selected_node: KnowledgeGraphNode;
  nodes: KnowledgeGraphNode[];
  edges: KnowledgeGraphEdge[];
};

export function getGraphNodes(limit = 200): Promise<GraphNodeListResponse> {
  return getJson<GraphNodeListResponse>(`/api/v1/graph/nodes?limit=${limit}`);
}

export function getGraphEdges(limit = 200): Promise<GraphEdgeListResponse> {
  return getJson<GraphEdgeListResponse>(`/api/v1/graph/edges?limit=${limit}`);
}

export function getGraphNeighborhood(nodeId: string, depth = 1): Promise<GraphNeighborhoodResponse> {
  return getJson<GraphNeighborhoodResponse>(
    `/api/v1/graph/neighborhood?node_id=${encodeURIComponent(nodeId)}&depth=${depth}`
  );
}
