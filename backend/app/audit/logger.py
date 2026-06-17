from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import AuditEventType, ErrorCode
from backend.app.schemas.operational import AuditEvent


class AuditLogger:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.settings.ensure_data_dirs()
        self.audit_file = self.settings.audit_dir / "audit.jsonl"

    def write(
        self,
        *,
        event_type: AuditEventType,
        request_id: str,
        outcome: str,
        resource_ids: list[str] | None = None,
        details: dict[str, Any] | None = None,
        error_code: ErrorCode | None = None,
        duration_ms: int | None = None,
    ) -> None:
        event = AuditEvent(
            event_type=event_type,
            request_id=request_id,
            outcome=outcome,
            resource_ids=resource_ids or [],
            details=self._redact(details or {}),
            error_code=error_code,
            duration_ms=duration_ms,
        )
        self._append_jsonl(self.audit_file, event.model_dump(mode="json"))

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")

    @staticmethod
    def _redact(details: dict[str, Any]) -> dict[str, Any]:
        blocked = {"content", "text", "document_body", "raw_content"}
        return {key: value for key, value in details.items() if key not in blocked}

