from __future__ import annotations

from datetime import date

from pydantic import Field, model_validator

from .documents import ChunkMetadata, StrictBaseModel


class Citation(StrictBaseModel):
    citation_id: str = Field(min_length=1, max_length=40)
    doc_id: str = Field(min_length=3, max_length=100)
    chunk_id: str = Field(min_length=3, max_length=200)
    title: str = Field(min_length=3, max_length=200)
    section_title: str = Field(min_length=1, max_length=200)
    source_file: str = Field(min_length=1, max_length=500)
    version: str = Field(min_length=1, max_length=40)
    effective_date: date
    quote: str = Field(min_length=1, max_length=4000)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    quote_hash: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def validate_offsets(self) -> "Citation":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self


class RetrievalResult(StrictBaseModel):
    chunk_id: str
    doc_id: str
    text: str
    metadata: ChunkMetadata
    vector_score: float | None = Field(default=None, ge=0.0, le=1.0)
    bm25_score: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata_boost: float = Field(default=0.0, ge=0.0, le=1.0)
    recency_boost: float = Field(default=1.0, ge=0.0, le=1.0)
    hybrid_score: float = Field(ge=0.0, le=1.0)
    rank: int = Field(ge=1)
    citation: Citation

