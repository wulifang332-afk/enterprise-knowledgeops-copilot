from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.api import (
    chunks_router,
    documents_router,
    evaluation_router,
    feedback_router,
    graph_router,
    ingest_router,
    query_router,
    readiness_router,
    search_router,
    studio_router,
)
from backend.app.core.errors import KnowledgeOpsError
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.operational import ErrorResponse


def create_app() -> FastAPI:
    app = FastAPI(
        title="Enterprise KnowledgeOps Copilot API",
        version="0.7.0",
        description=(
            "Phase 7 API for ingestion, retrieval, graph inspection, governed query answering, "
            "deterministic quality evaluation, and local feedback governance."
        ),
    )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        incoming = request.headers.get("X-Request-ID")
        request_id = incoming if _is_uuid(incoming) else str(uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.add_exception_handler(KnowledgeOpsError, knowledgeops_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.include_router(ingest_router)
    app.include_router(documents_router)
    app.include_router(chunks_router)
    app.include_router(search_router)
    app.include_router(graph_router)
    app.include_router(query_router)
    app.include_router(readiness_router)
    app.include_router(evaluation_router)
    app.include_router(feedback_router)
    app.include_router(studio_router)
    return app


async def knowledgeops_exception_handler(request: Request, exc: KnowledgeOpsError) -> JSONResponse:
    status_code = _status_code_for(exc.error_code)
    return _error_response(
        request,
        status_code=status_code,
        error_code=exc.error_code,
        message=exc.message,
        details=exc.details,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(
        request,
        status_code=422,
        error_code=ErrorCode.INVALID_REQUEST,
        message="Request validation failed.",
        details={"errors": exc.errors()},
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return _error_response(
        request,
        status_code=exc.status_code,
        error_code=ErrorCode.INVALID_REQUEST if exc.status_code < 500 else ErrorCode.INTERNAL_ERROR,
        message=str(exc.detail),
        details={},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error_response(
        request,
        status_code=500,
        error_code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error.",
        details={},
    )


def _error_response(
    request: Request,
    *,
    status_code: int,
    error_code: ErrorCode,
    message: str,
    details: dict,
) -> JSONResponse:
    payload = ErrorResponse(
        error_code=error_code,
        message=message,
        details=details,
        request_id=str(getattr(request.state, "request_id", str(uuid4()))),
        timestamp=datetime.now(timezone.utc),
    )
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


def _status_code_for(error_code: ErrorCode) -> int:
    return {
        ErrorCode.INVALID_REQUEST: 400,
        ErrorCode.INVALID_METADATA: 422,
        ErrorCode.INVALID_FILE_PATH: 400,
        ErrorCode.UNSUPPORTED_FILE_TYPE: 415,
        ErrorCode.DUPLICATE_DOCUMENT: 409,
        ErrorCode.EMPTY_DOCUMENT: 422,
        ErrorCode.INDEX_UNAVAILABLE: 503,
        ErrorCode.EMBEDDING_PROVIDER_UNAVAILABLE: 503,
        ErrorCode.LLM_PROVIDER_UNAVAILABLE: 503,
        ErrorCode.GRAPH_UNAVAILABLE: 503,
        ErrorCode.ACCESS_DENIED: 403,
        ErrorCode.INSUFFICIENT_EVIDENCE: 422,
        ErrorCode.CITATION_VALIDATION_FAILED: 422,
        ErrorCode.INVALID_EVALUATION_CASE: 422,
        ErrorCode.INTERNAL_ERROR: 500,
    }.get(error_code, 500)


def _is_uuid(value: str | None) -> bool:
    if not value:
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


app = create_app()
