from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import get_evaluation_service
from backend.app.api.utils import request_id_from
from backend.app.evaluation.schema import EvaluationCasesResponse, EvaluationReportResponse
from backend.app.evaluation.service import EvaluationService

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.post("/run", response_model=EvaluationReportResponse)
def run_evaluation(
    request: Request,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationReportResponse:
    return EvaluationReportResponse(
        request_id=request_id_from(request),
        report=service.run(persist=True),
    )


@router.get("/latest", response_model=EvaluationReportResponse)
def latest_evaluation(
    request: Request,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationReportResponse:
    return EvaluationReportResponse(
        request_id=request_id_from(request),
        report=service.latest_report(),
    )


@router.get("/cases", response_model=EvaluationCasesResponse)
def evaluation_cases(
    request: Request,
    service: EvaluationService = Depends(get_evaluation_service),
) -> EvaluationCasesResponse:
    dataset = service.list_cases()
    return EvaluationCasesResponse(
        request_id=request_id_from(request),
        dataset_version=dataset.dataset_version,
        total_cases=len(dataset.cases),
        items=dataset.cases,
    )
