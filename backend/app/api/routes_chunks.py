from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.app.api.dependencies import get_settings
from backend.app.api.utils import ProcessedRegistryReader, clamp_pagination, matches_text_filter, paginate, request_id_from
from backend.app.core.settings import AppSettings
from backend.app.schemas.api import ChunkSummary, PaginatedChunksResponse

router = APIRouter(prefix="/api/v1", tags=["chunks"])


@router.get("/chunks", response_model=PaginatedChunksResponse)
def list_chunks(
    request: Request,
    doc_id: str | None = None,
    section_title: str | None = None,
    department: str | None = None,
    region: str | None = None,
    policy_type: str | None = None,
    access_level: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    settings: AppSettings = Depends(get_settings),
) -> PaginatedChunksResponse:
    offset, limit = clamp_pagination(offset, limit)
    chunks = ProcessedRegistryReader(settings).chunks()
    filtered = [
        chunk
        for chunk in chunks
        if _matches(chunk, doc_id, section_title, department, region, policy_type, access_level)
    ]
    return PaginatedChunksResponse(
        request_id=request_id_from(request),
        total=len(filtered),
        offset=offset,
        limit=limit,
        items=[ChunkSummary.model_validate(chunk.model_dump()) for chunk in paginate(filtered, offset=offset, limit=limit)],
    )


def _matches(
    chunk: ChunkSummary,
    doc_id: str | None,
    section_title: str | None,
    department: str | None,
    region: str | None,
    policy_type: str | None,
    access_level: str | None,
) -> bool:
    metadata = chunk.metadata
    return (
        matches_text_filter(metadata.doc_id, doc_id)
        and matches_text_filter(metadata.section_title, section_title, contains=True)
        and matches_text_filter(metadata.department, department)
        and (region is None or any(matches_text_filter(item, region) for item in metadata.regions))
        and matches_text_filter(metadata.policy_type.value, policy_type)
        and matches_text_filter(metadata.access_level.value, access_level)
    )
