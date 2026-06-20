from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import Field, field_validator

from backend.app.query.schema import AnswerGenerationStatus, EvidencePackStatus, QueryIntent, QueryRoute
from backend.app.schemas.documents import StrictBaseModel
from backend.app.schemas.retrieval import Citation


class UserRating(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class FeedbackType(StrEnum):
    ANSWER_QUALITY = "answer_quality"
    CITATION_ISSUE = "citation_issue"
    RETRIEVAL_ISSUE = "retrieval_issue"
    GRAPH_ISSUE = "graph_issue"
    REFUSAL_ISSUE = "refusal_issue"
    ROUTING_ISSUE = "routing_issue"
    UI_ISSUE = "ui_issue"
    OTHER = "other"


class IssueCategory(StrEnum):
    MISSING_EVIDENCE = "missing_evidence"
    WRONG_CITATION = "wrong_citation"
    UNSUPPORTED_ANSWER = "unsupported_answer"
    INCORRECT_REFUSAL = "incorrect_refusal"
    SHOULD_HAVE_REFUSED = "should_have_refused"
    WRONG_INTENT = "wrong_intent"
    WRONG_ROUTE = "wrong_route"
    IRRELEVANT_GRAPH_CONTEXT = "irrelevant_graph_context"
    STALE_DOCUMENT = "stale_document"
    UNCLEAR_ANSWER = "unclear_answer"
    OTHER = "other"


class ReviewStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    RESOLVED = "resolved"
    WONT_FIX = "wont_fix"


class FeedbackSource(StrEnum):
    API = "api"
    QUERY_PLANNER = "query_planner"
    EVALUATION_DASHBOARD = "evaluation_dashboard"
    MANUAL = "manual"


class FeedbackCreateRequest(StrictBaseModel):
    query: str = Field(min_length=2, max_length=2000)
    request_id: str | None = Field(default=None, min_length=1, max_length=120)
    intent: QueryIntent | None = None
    route: QueryRoute | None = None
    status: EvidencePackStatus | None = None
    answer_generation_status: AnswerGenerationStatus | None = None
    answer: str | None = Field(default=None, max_length=4000)
    citations: list[Citation] = Field(default_factory=list, max_length=20)
    answer_citations: list[Citation] = Field(default_factory=list, max_length=20)
    user_rating: UserRating
    feedback_type: FeedbackType
    issue_category: IssueCategory
    comment: str = Field(min_length=1, max_length=2000)
    linked_eval_case_id: str | None = Field(default=None, min_length=1, max_length=120)
    source: FeedbackSource = FeedbackSource.API
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("query", "comment", "request_id", "linked_eval_case_id", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = str(value).strip()
        return stripped or None


class FeedbackRecord(FeedbackCreateRequest):
    feedback_id: str = Field(default_factory=lambda: f"fb:{uuid4()}", min_length=3, max_length=80)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    review_status: ReviewStatus = ReviewStatus.OPEN
    reviewer_note: str | None = Field(default=None, max_length=2000)


class FeedbackUpdateRequest(StrictBaseModel):
    review_status: ReviewStatus | None = None
    reviewer_note: str | None = Field(default=None, max_length=2000)
    linked_eval_case_id: str | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("reviewer_note", "linked_eval_case_id", mode="before")
    @classmethod
    def strip_update_text(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = str(value).strip()
        return stripped or None


class FeedbackListFilters(StrictBaseModel):
    review_status: ReviewStatus | None = None
    feedback_type: FeedbackType | None = None
    issue_category: IssueCategory | None = None
    user_rating: UserRating | None = None


class FeedbackSummary(StrictBaseModel):
    total_count: int = 0
    negative_count: int = 0
    unresolved_count: int = 0
    by_issue_category: dict[str, int] = Field(default_factory=dict)
    by_review_status: dict[str, int] = Field(default_factory=dict)
    by_feedback_type: dict[str, int] = Field(default_factory=dict)
    top_issue_categories: list[dict[str, int | str]] = Field(default_factory=list)


class FeedbackCreateResponse(StrictBaseModel):
    request_id: str
    feedback_id: str
    record: FeedbackRecord


class FeedbackRecordResponse(StrictBaseModel):
    request_id: str
    record: FeedbackRecord


class FeedbackListResponse(StrictBaseModel):
    request_id: str
    total: int
    offset: int
    limit: int
    items: list[FeedbackRecord]
    summary: FeedbackSummary

