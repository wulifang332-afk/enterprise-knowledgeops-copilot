import type { Citation } from "./search";
import { getJson } from "./client";

export type UserRating = "positive" | "negative" | "neutral";

export type FeedbackType =
  | "answer_quality"
  | "citation_issue"
  | "retrieval_issue"
  | "graph_issue"
  | "refusal_issue"
  | "routing_issue"
  | "ui_issue"
  | "other";

export type IssueCategory =
  | "missing_evidence"
  | "wrong_citation"
  | "unsupported_answer"
  | "incorrect_refusal"
  | "should_have_refused"
  | "wrong_intent"
  | "wrong_route"
  | "irrelevant_graph_context"
  | "stale_document"
  | "unclear_answer"
  | "other";

export type ReviewStatus = "open" | "triaged" | "resolved" | "wont_fix";

export type FeedbackSource = "api" | "query_planner" | "evaluation_dashboard" | "manual";

export type FeedbackRecord = {
  query: string;
  request_id: string | null;
  intent: string | null;
  route: string | null;
  status: string | null;
  answer_generation_status: string | null;
  answer: string | null;
  citations: Citation[];
  answer_citations: Citation[];
  user_rating: UserRating;
  feedback_type: FeedbackType;
  issue_category: IssueCategory;
  comment: string;
  linked_eval_case_id: string | null;
  source: FeedbackSource;
  metadata: Record<string, unknown>;
  feedback_id: string;
  timestamp: string;
  review_status: ReviewStatus;
  reviewer_note: string | null;
};

export type FeedbackSummary = {
  total_count: number;
  negative_count: number;
  unresolved_count: number;
  by_issue_category: Record<string, number>;
  by_review_status: Record<string, number>;
  by_feedback_type: Record<string, number>;
  top_issue_categories: Array<Record<string, number | string>>;
};

export type FeedbackListResponse = {
  request_id: string;
  total: number;
  offset: number;
  limit: number;
  items: FeedbackRecord[];
  summary: FeedbackSummary;
};

export function getFeedbackList(limit = 500): Promise<FeedbackListResponse> {
  return getJson<FeedbackListResponse>(`/api/v1/feedback?limit=${limit}`);
}
