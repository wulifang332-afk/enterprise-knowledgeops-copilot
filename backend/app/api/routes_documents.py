from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.app.api.dependencies import get_settings
from backend.app.api.utils import ProcessedRegistryReader, clamp_pagination, matches_text_filter, paginate, request_id_from
from backend.app.core.settings import AppSettings
from backend.app.schemas.api import DocumentSummary, PaginatedDocumentsResponse

router = APIRouter(prefix="/api/v1", tags=["documents"])


@router.get("/documents", response_model=PaginatedDocumentsResponse)
def list_documents(
    request: Request,
    department: str | None = None,
    region: str | None = None,
    policy_type: str | None = None,
    access_level: str | None = None,
    owner: str | None = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    settings: AppSettings = Depends(get_settings),
) -> PaginatedDocumentsResponse:
    offset, limit = clamp_pagination(offset, limit)
    documents = ProcessedRegistryReader(settings).documents()
    filtered = [
        document
        for document in documents
        if _matches(document, department, region, policy_type, access_level, owner)
    ]
    return PaginatedDocumentsResponse(
        request_id=request_id_from(request),
        total=len(filtered),
        offset=offset,
        limit=limit,
        items=paginate(filtered, offset=offset, limit=limit),
    )


def _matches(
    document: DocumentSummary,
    department: str | None,
    region: str | None,
    policy_type: str | None,
    access_level: str | None,
    owner: str | None,
) -> bool:
    metadata = document.metadata
    return (
        matches_text_filter(metadata.department, department)
        and (region is None or any(matches_text_filter(item, region) for item in metadata.regions))
        and matches_text_filter(metadata.policy_type.value, policy_type)
        and matches_text_filter(metadata.access_level.value, access_level)
        and matches_text_filter(metadata.owner, owner)
    )
