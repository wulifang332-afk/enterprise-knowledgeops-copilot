from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import AuditEventType, ErrorCode, IngestionStatus


class OperationalBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorResponse(OperationalBaseModel):
    error_code: ErrorCode
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IngestionFileResult(OperationalBaseModel):
    source_file: str
    status: IngestionStatus
    doc_id: str | None = None
    content_sha256: str | None = None
    chunk_count: int = 0
    section_count: int = 0
    error_code: ErrorCode | None = None
    message: str = ""


class IngestionSummary(OperationalBaseModel):
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    total_files: int = 0
    ingested_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    results: list[IngestionFileResult] = Field(default_factory=list)


class AuditEvent(OperationalBaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: AuditEventType
    request_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    actor_id: str | None = None
    outcome: str
    resource_ids: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    error_code: ErrorCode | None = None
    duration_ms: int | None = None

