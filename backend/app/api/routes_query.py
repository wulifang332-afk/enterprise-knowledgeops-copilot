from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import get_query_planning_service
from backend.app.api.utils import request_id_from
from backend.app.query.schema import EvidencePack, QueryRequest
from backend.app.query.service import QueryPlanningService

router = APIRouter(prefix="/api/v1", tags=["query-planning"])


@router.post("/query", response_model=EvidencePack)
def query(
    payload: QueryRequest,
    request: Request,
    service: QueryPlanningService = Depends(get_query_planning_service),
) -> EvidencePack:
    return service.plan(request=payload, request_id=request_id_from(request))
