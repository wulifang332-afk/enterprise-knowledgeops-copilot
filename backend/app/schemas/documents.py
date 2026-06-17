from __future__ import annotations

import re
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .enums import AccessLevel, PolicyType

ID_PATTERN = r"^[a-z0-9][a-z0-9:_-]{1,149}$"
SHA256_PATTERN = r"^[a-f0-9]{64}$"


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class DocumentMetadata(StrictBaseModel):
    doc_id: str = Field(min_length=3, max_length=100, pattern=ID_PATTERN)
    title: str = Field(min_length=3, max_length=200)
    department: str = Field(min_length=2, max_length=100)
    regions: list[str] = Field(min_length=1, max_length=10)
    policy_type: PolicyType
    effective_date: date
    version: str = Field(min_length=1, max_length=40)
    access_level: AccessLevel
    owner: str = Field(min_length=2, max_length=120)
    source_file: str = Field(min_length=1, max_length=500)
    related_processes: list[str] = Field(default_factory=list, max_length=20)
    created_at: datetime
    updated_at: datetime
    content_sha256: str = Field(pattern=SHA256_PATTERN)

    @field_validator("title", "department", "version", "owner", "source_file")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field cannot be blank")
        return stripped

    @field_validator("regions", "related_processes")
    @classmethod
    def normalize_string_list(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in value:
            stripped = str(item).strip()
            if not stripped:
                continue
            key = stripped.casefold()
            if key not in seen:
                normalized.append(stripped)
                seen.add(key)
        if not normalized and value:
            raise ValueError("list cannot contain only blank values")
        return normalized

    @model_validator(mode="after")
    def validate_dates_and_source(self) -> "DocumentMetadata":
        if self.updated_at < self.created_at:
            raise ValueError("updated_at must be at or after created_at")
        if self.source_file.startswith("/") or ".." in self.source_file.split("/"):
            raise ValueError("source_file must be a safe project-relative path")
        if not self.source_file.startswith("data/raw/"):
            raise ValueError("source_file must be derived from data/raw/")
        return self


class Section(StrictBaseModel):
    section_id: str = Field(pattern=ID_PATTERN)
    doc_id: str = Field(pattern=ID_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    heading_level: int = Field(ge=1, le=6)
    heading_occurrence: int = Field(ge=1)
    section_path: list[str] = Field(min_length=1)
    section_path_hash: str = Field(min_length=8, max_length=16)
    text: str = Field(min_length=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_offsets(self) -> "Section":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        return self


class ChunkMetadata(DocumentMetadata):
    chunk_id: str = Field(pattern=ID_PATTERN)
    section_title: str = Field(min_length=1, max_length=200)
    section_path: list[str] = Field(min_length=1)
    section_path_hash: str = Field(min_length=8, max_length=16)
    heading_occurrence: int = Field(ge=1)
    related_process: str | None = Field(default=None, max_length=120)
    chunk_index: int = Field(ge=1)

    @field_validator("chunk_id")
    @classmethod
    def validate_chunk_id(cls, value: str) -> str:
        if not re.match(ID_PATTERN, value):
            raise ValueError("invalid chunk_id")
        return value


class Chunk(StrictBaseModel):
    chunk_id: str = Field(pattern=ID_PATTERN)
    doc_id: str = Field(pattern=ID_PATTERN)
    text: str = Field(min_length=1)
    metadata: ChunkMetadata
    token_count: int = Field(ge=1)
    start_char: int = Field(ge=0)
    end_char: int = Field(gt=0)
    text_sha256: str = Field(pattern=SHA256_PATTERN)

    @model_validator(mode="after")
    def validate_chunk(self) -> "Chunk":
        if self.end_char <= self.start_char:
            raise ValueError("end_char must be greater than start_char")
        if self.chunk_id != self.metadata.chunk_id:
            raise ValueError("chunk_id must match metadata.chunk_id")
        if self.doc_id != self.metadata.doc_id:
            raise ValueError("doc_id must match metadata.doc_id")
        return self


class Document(StrictBaseModel):
    metadata: DocumentMetadata
    content: str = Field(min_length=1)
    sections: list[Section] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    ingested_at: datetime

