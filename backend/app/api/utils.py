from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import Request

from backend.app.core.settings import AppSettings
from backend.app.schemas.documents import Chunk, DocumentMetadata
from backend.app.schemas.api import DocumentSummary


def request_id_from(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown-request"))


def clamp_pagination(offset: int, limit: int) -> tuple[int, int]:
    offset = max(0, offset)
    limit = max(1, min(limit, 200))
    return offset, limit


def paginate(items: list[Any], *, offset: int, limit: int) -> list[Any]:
    return items[offset : offset + limit]


class ProcessedRegistryReader:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def documents(self) -> list[DocumentSummary]:
        items: list[DocumentSummary] = []
        for path in self._processed_files():
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                DocumentSummary(
                    metadata=DocumentMetadata.model_validate(payload["metadata"]),
                    section_count=len(payload.get("sections", [])),
                    chunk_count=len(payload.get("chunks", [])),
                )
            )
        return sorted(items, key=lambda item: item.metadata.doc_id)

    def chunks(self) -> list[Chunk]:
        items: list[Chunk] = []
        for path in self._processed_files():
            payload = json.loads(path.read_text(encoding="utf-8"))
            items.extend(Chunk.model_validate(chunk) for chunk in payload.get("chunks", []))
        return sorted(items, key=lambda item: item.chunk_id)

    def _processed_files(self) -> list[Path]:
        if not self.settings.processed_dir.exists():
            return []
        return sorted(self.settings.processed_dir.glob("*.json"))


def matches_text_filter(actual: str, expected: str | None, *, contains: bool = False) -> bool:
    if expected is None:
        return True
    if contains:
        return expected.casefold() in actual.casefold()
    return actual.casefold() == expected.casefold()

