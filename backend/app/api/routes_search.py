from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import get_retrieval_search_service
from backend.app.api.utils import request_id_from
from backend.app.retrieval.service import RetrievalSearchService
from backend.app.schemas.api import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.post("/search", response_model=SearchResponse)
def search(
    payload: SearchRequest,
    request: Request,
    service: RetrievalSearchService = Depends(get_retrieval_search_service),
) -> SearchResponse:
    outcome = service.search(
        query=payload.query,
        retrieval_mode=payload.retrieval_mode,
        top_k=payload.top_k,
        filters=payload.filters.active_dict(),
    )
    return SearchResponse(
        request_id=request_id_from(request),
        query=payload.query,
        retrieval_mode=payload.retrieval_mode,
        top_k=payload.top_k,
        degraded=outcome.degraded,
        degraded_reasons=outcome.degraded_reasons,
        results=outcome.results,
    )
