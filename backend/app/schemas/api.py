from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from .documents import Chunk, DocumentMetadata, StrictBaseModel
from .operational import IngestionFileResult
from .retrieval import RetrievalResult


class IngestRequest(StrictBaseModel):
    files: list[str] | None = Field(default=None, max_length=50)
    ingest_all: bool = True
    rebuild_indexes: bool = True

    @field_validator("files")
    @classmethod
    def strip_files(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        return [item.strip() for item in value if item.strip()]


class SearchFilters(StrictBaseModel):
    doc_ids: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    regions: list[str] = Field(default_factory=list)
    policy_types: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    access_levels: list[str] = Field(default_factory=list)
    section_titles: list[str] = Field(default_factory=list)
    related_processes: list[str] = Field(default_factory=list)

    @field_validator(
        "doc_ids",
        "departments",
        "regions",
        "policy_types",
        "owners",
        "access_levels",
        "section_titles",
        "related_processes",
    )
    @classmethod
    def strip_list_values(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            stripped = item.strip()
            if not stripped:
                continue
            key = stripped.casefold()
            if key not in seen:
                cleaned.append(stripped)
                seen.add(key)
        return cleaned

    def active_dict(self) -> dict[str, list[str]]:
        return {key: value for key, value in self.model_dump().items() if value}


class IndexRebuildSummary(StrictBaseModel):
    attempted: bool = False
    succeeded: bool = False
    chunk_count: int = 0
    bm25_index: str | None = None
    chroma_index: str | None = None
    error: str | None = None


class IngestResponse(StrictBaseModel):
    request_id: str
    total_files: int
    ingested_count: int
    skipped_count: int
    failed_count: int
    results: list[IngestionFileResult]
    index_rebuild: IndexRebuildSummary


class DocumentSummary(StrictBaseModel):
    metadata: DocumentMetadata
    section_count: int
    chunk_count: int


class PaginatedDocumentsResponse(StrictBaseModel):
    request_id: str
    total: int
    offset: int
    limit: int
    items: list[DocumentSummary]


class ChunkSummary(Chunk):
    pass


class PaginatedChunksResponse(StrictBaseModel):
    request_id: str
    total: int
    offset: int
    limit: int
    items: list[ChunkSummary]


class SearchRequest(StrictBaseModel):
    query: str = Field(min_length=2, max_length=2000)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    top_k: int = Field(default=5, ge=1, le=20)
    retrieval_mode: Literal["bm25", "vector", "hybrid"] = "hybrid"


class SearchResponse(StrictBaseModel):
    request_id: str
    query: str
    retrieval_mode: Literal["bm25", "vector", "hybrid"]
    top_k: int
    degraded: bool
    degraded_reasons: list[str]
    results: list[RetrievalResult]
