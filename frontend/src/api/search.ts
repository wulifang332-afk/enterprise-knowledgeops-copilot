import type { DocumentMetadata } from "./documents";
import { postJson } from "./client";

export type SearchFilters = {
  doc_ids?: string[];
  departments?: string[];
  regions?: string[];
  policy_types?: string[];
  owners?: string[];
  access_levels?: string[];
  section_titles?: string[];
  related_processes?: string[];
};

export type SearchRequest = {
  query: string;
  filters: SearchFilters;
  top_k: number;
  retrieval_mode: "bm25" | "vector" | "hybrid";
};

export type Citation = {
  citation_id: string;
  doc_id: string;
  chunk_id: string;
  title: string;
  section_title: string;
  source_file: string;
  version: string;
  effective_date: string;
  quote: string;
  start_char: number;
  end_char: number;
  quote_hash: string;
};

export type ChunkMetadata = DocumentMetadata & {
  chunk_id: string;
  section_title: string;
  section_path: string[];
  section_path_hash: string;
  heading_occurrence: number;
  related_process: string | null;
  chunk_index: number;
};

export type RetrievalResult = {
  chunk_id: string;
  doc_id: string;
  text: string;
  metadata: ChunkMetadata;
  vector_score: number | null;
  bm25_score: number | null;
  metadata_boost: number;
  recency_boost: number;
  hybrid_score: number;
  rank: number;
  citation: Citation;
};

export type SearchResponse = {
  request_id: string;
  query: string;
  retrieval_mode: "bm25" | "vector" | "hybrid";
  top_k: number;
  degraded: boolean;
  degraded_reasons: string[];
  results: RetrievalResult[];
};

export function searchKnowledge(query: string): Promise<SearchResponse> {
  return postJson<SearchResponse, SearchRequest>("/api/v1/search", {
    query,
    filters: {},
    top_k: 5,
    retrieval_mode: "hybrid"
  });
}
