import { getJson } from "./client";

export type DocumentMetadata = {
  doc_id: string;
  title: string;
  department: string;
  regions: string[];
  policy_type: string;
  effective_date: string;
  version: string;
  access_level: string;
  owner: string;
  source_file: string;
  related_processes: string[];
  created_at: string;
  updated_at: string;
  content_sha256: string;
};

export type DocumentSummary = {
  metadata: DocumentMetadata;
  section_count: number;
  chunk_count: number;
};

export type PaginatedDocumentsResponse = {
  request_id: string;
  total: number;
  offset: number;
  limit: number;
  items: DocumentSummary[];
};

export function getDocuments(limit = 200): Promise<PaginatedDocumentsResponse> {
  return getJson<PaginatedDocumentsResponse>(`/api/v1/documents?limit=${limit}`);
}
