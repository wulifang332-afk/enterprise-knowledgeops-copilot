from __future__ import annotations

from typing import Any

from backend.app.schemas.enums import ErrorCode


class KnowledgeOpsError(Exception):
    """Typed application error that maps cleanly to future API responses."""

    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }

