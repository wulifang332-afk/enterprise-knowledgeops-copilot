import type { ChunkMetadata, Citation, SearchFilters } from "./search";
import { postJson } from "./client";

export type QueryRequest = {
  query: string;
  top_k: number;
  include_graph: boolean;
  generate_answer: boolean;
  filters: SearchFilters;
};

export type RetrievalEvidenceItem = {
  rank: number;
  chunk_id: string;
  doc_id: string;
  title: string;
  section_title: string;
  source_document_metadata: ChunkMetadata;
  bm25_score: number | null;
  vector_score: number | null;
  hybrid_score: number;
  citation: Citation;
  quote: string;
  source_text_excerpt: string;
};

export type GraphNode = {
  node_id: string;
  label: string;
  type: string;
  source_doc_ids: string[];
  source_chunk_ids: string[];
  mentions: string[];
  confidence: number;
  created_by: string;
};

export type GraphEdge = {
  edge_id: string;
  source_node_id: string;
  target_node_id: string;
  relation_type: string;
  source_doc_id: string;
  source_chunk_id: string;
  evidence_quote: string;
  confidence: number;
  created_by: string;
};

export type GraphEvidence = {
  matched_nodes: GraphNode[];
  neighboring_nodes: GraphNode[];
  edges: GraphEdge[];
  relation_types: string[];
};

export type EvidencePack = {
  request_id: string;
  query: string;
  intent: string;
  route: string;
  status: string;
  retrieval_evidence: RetrievalEvidenceItem[];
  graph_evidence: GraphEvidence;
  citations: Citation[];
  refusal_reason: string | null;
  limitations: string[];
  next_phase_note: string;
  answer: string | null;
  answer_citations: Citation[];
  answer_generation_status: string;
  answer_refusal_reason: string | null;
  grounding_summary: string | null;
};

export function planQuery(query: string, generateAnswer: boolean, filters: SearchFilters = {}): Promise<EvidencePack> {
  return postJson<EvidencePack, QueryRequest>("/api/v1/query", {
    query,
    top_k: 5,
    include_graph: true,
    generate_answer: generateAnswer,
    filters
  });
}
