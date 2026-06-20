from __future__ import annotations

from backend.app.audit.logger import AuditLogger
from backend.app.core.settings import AppSettings
from backend.app.feedback.schema import (
    FeedbackCreateRequest,
    FeedbackListFilters,
    FeedbackRecord,
    FeedbackSummary,
    FeedbackUpdateRequest,
)
from backend.app.feedback.store import FeedbackStore
from backend.app.schemas.enums import AuditEventType


class FeedbackService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.store = FeedbackStore(settings)
        self.audit = AuditLogger(settings)

    def submit(self, request: FeedbackCreateRequest, *, request_id: str) -> FeedbackRecord:
        record = self.store.append(request)
        self.audit.write(
            event_type=AuditEventType.FEEDBACK_SUBMISSION,
            request_id=request_id,
            outcome="success",
            resource_ids=[record.feedback_id],
            feedback_id=record.feedback_id,
            summary="Feedback submitted.",
            metadata={
                "feedback_type": record.feedback_type.value,
                "issue_category": record.issue_category.value,
                "user_rating": record.user_rating.value,
                "source": record.source.value,
            },
        )
        return record

    def list_feedback(
        self,
        filters: FeedbackListFilters | None = None,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[FeedbackRecord], int, FeedbackSummary]:
        return self.store.list_filtered(filters, offset=offset, limit=limit)

    def get(self, feedback_id: str) -> FeedbackRecord:
        return self.store.get(feedback_id)

    def update(self, feedback_id: str, request: FeedbackUpdateRequest, *, request_id: str) -> FeedbackRecord:
        record, changed_fields = self.store.update(feedback_id, request)
        if "review_status" in changed_fields:
            self.audit.write(
                event_type=AuditEventType.FEEDBACK_STATUS_UPDATED,
                request_id=request_id,
                outcome="success",
                resource_ids=[record.feedback_id],
                feedback_id=record.feedback_id,
                summary="Feedback review status updated.",
                metadata={"review_status": record.review_status.value},
            )
        if "reviewer_note" in changed_fields:
            self.audit.write(
                event_type=AuditEventType.FEEDBACK_REVIEWER_NOTE_UPDATED,
                request_id=request_id,
                outcome="success",
                resource_ids=[record.feedback_id],
                feedback_id=record.feedback_id,
                summary="Feedback reviewer note updated.",
            )
        if "linked_eval_case_id" in changed_fields:
            self.audit.write(
                event_type=AuditEventType.FEEDBACK_EVAL_LINKED,
                request_id=request_id,
                outcome="success",
                resource_ids=[record.feedback_id],
                feedback_id=record.feedback_id,
                summary="Feedback linked to evaluation case.",
                metadata={"linked_eval_case_id": record.linked_eval_case_id},
            )
        return record

