from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from backend.app.api.dependencies import get_index_rebuild_service, get_ingestion_service
from backend.app.api.utils import request_id_from
from backend.app.core.errors import KnowledgeOpsError
from backend.app.ingestion.service import IngestionService
from backend.app.retrieval.indexing import IndexRebuildService
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.api import IngestRequest, IngestResponse, IndexRebuildSummary

router = APIRouter(prefix="/api/v1", tags=["ingestion"])


@router.post("/ingest", response_model=IngestResponse)
def ingest_documents(
    payload: IngestRequest,
    request: Request,
    service: IngestionService = Depends(get_ingestion_service),
    index_service: IndexRebuildService = Depends(get_index_rebuild_service),
) -> IngestResponse:
    request_id = request_id_from(request)
    paths = payload.files or []
    if paths:
        summary = service.ingest_paths(paths, request_id=request_id)
    elif payload.ingest_all:
        summary = service.ingest_all_raw(request_id=request_id)
    else:
        raise KnowledgeOpsError(
            ErrorCode.INVALID_REQUEST,
            "Provide at least one file or set ingest_all=true.",
            {"files": paths, "ingest_all": payload.ingest_all},
        )

    index_summary = IndexRebuildSummary(attempted=payload.rebuild_indexes)
    if payload.rebuild_indexes:
        try:
            result = index_service.rebuild_all()
            index_summary = IndexRebuildSummary(
                attempted=True,
                succeeded=True,
                chunk_count=result.chunk_count,
                bm25_index=result.bm25_index,
                chroma_index=result.chroma_index,
            )
        except KnowledgeOpsError as exc:
            index_summary = IndexRebuildSummary(
                attempted=True,
                succeeded=False,
                error=f"{exc.error_code.value}: {exc.message}",
            )

    return IngestResponse(
        request_id=request_id,
        total_files=summary.total_files,
        ingested_count=summary.ingested_count,
        skipped_count=summary.skipped_count,
        failed_count=summary.failed_count,
        results=summary.results,
        index_rebuild=index_summary,
    )
