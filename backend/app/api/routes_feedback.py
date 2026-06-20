from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.api.dependencies import get_feedback_service
from backend.app.api.utils import request_id_from
from backend.app.feedback.schema import (
    FeedbackCreateRequest,
    FeedbackCreateResponse,
    FeedbackListFilters,
    FeedbackListResponse,
    FeedbackRecordResponse,
    FeedbackType,
    FeedbackUpdateRequest,
    IssueCategory,
    ReviewStatus,
    UserRating,
)
from backend.app.feedback.service import FeedbackService

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("", response_model=FeedbackCreateResponse)
def submit_feedback(
    payload: FeedbackCreateRequest,
    request: Request,
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackCreateResponse:
    record = service.submit(payload, request_id=request_id_from(request))
    return FeedbackCreateResponse(
        request_id=request_id_from(request),
        feedback_id=record.feedback_id,
        record=record,
    )


@router.get("", response_model=FeedbackListResponse)
def list_feedback(
    request: Request,
    review_status: ReviewStatus | None = None,
    feedback_type: FeedbackType | None = None,
    issue_category: IssueCategory | None = None,
    user_rating: UserRating | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackListResponse:
    filters = FeedbackListFilters(
        review_status=review_status,
        feedback_type=feedback_type,
        issue_category=issue_category,
        user_rating=user_rating,
    )
    items, total, summary = service.list_feedback(filters, offset=offset, limit=limit)
    return FeedbackListResponse(
        request_id=request_id_from(request),
        total=total,
        offset=offset,
        limit=limit,
        items=items,
        summary=summary,
    )


@router.get("/{feedback_id}", response_model=FeedbackRecordResponse)
def get_feedback(
    request: Request,
    feedback_id: str = Path(min_length=3, max_length=80),
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackRecordResponse:
    return FeedbackRecordResponse(
        request_id=request_id_from(request),
        record=service.get(feedback_id),
    )


@router.patch("/{feedback_id}", response_model=FeedbackRecordResponse)
def update_feedback(
    payload: FeedbackUpdateRequest,
    request: Request,
    feedback_id: str = Path(min_length=3, max_length=80),
    service: FeedbackService = Depends(get_feedback_service),
) -> FeedbackRecordResponse:
    return FeedbackRecordResponse(
        request_id=request_id_from(request),
        record=service.update(feedback_id, payload, request_id=request_id_from(request)),
    )
