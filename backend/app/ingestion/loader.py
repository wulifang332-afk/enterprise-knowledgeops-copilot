from __future__ import annotations

from pathlib import Path

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode

from .utils import normalize_text


class DocumentLoader:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.settings.ensure_data_dirs()

    def list_raw_files(self) -> list[str]:
        raw_root = self.settings.raw_dir.resolve()
        files: list[str] = []
        for path in sorted(self.settings.raw_dir.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.settings.allowed_file_types:
                continue
            resolved = path.resolve()
            try:
                resolved.relative_to(raw_root)
            except ValueError:
                continue
            files.append(resolved.relative_to(raw_root).as_posix())
        return files

    def load_relative_file(self, relative_path: str) -> tuple[Path, str, str]:
        resolved_path = self.resolve_raw_path(relative_path)
        raw_text = resolved_path.read_text(encoding="utf-8-sig")
        normalized = normalize_text(raw_text)
        if not normalized.strip():
            raise KnowledgeOpsError(
                ErrorCode.EMPTY_DOCUMENT,
                "Document is empty after normalization.",
                {"path": relative_path},
            )
        source_file = self._source_file_from_resolved_path(resolved_path)
        return resolved_path, source_file, normalized

    def resolve_raw_path(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise KnowledgeOpsError(
                ErrorCode.INVALID_FILE_PATH,
                "Absolute paths are not allowed for ingestion.",
                {"path": relative_path},
            )

        raw_root = self.settings.raw_dir.resolve()
        try:
            candidate = (raw_root / requested).resolve(strict=True)
        except FileNotFoundError as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_FILE_PATH,
                "Requested file does not exist under data/raw.",
                {"path": relative_path},
            ) from exc

        try:
            candidate.relative_to(raw_root)
        except ValueError as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_FILE_PATH,
                "Requested file resolves outside data/raw.",
                {"path": relative_path},
            ) from exc

        if not candidate.is_file():
            raise KnowledgeOpsError(
                ErrorCode.INVALID_FILE_PATH,
                "Requested path is not a file.",
                {"path": relative_path},
            )

        if candidate.suffix.lower() not in self.settings.allowed_file_types:
            raise KnowledgeOpsError(
                ErrorCode.UNSUPPORTED_FILE_TYPE,
                "Unsupported file type for Phase 1 ingestion.",
                {
                    "path": relative_path,
                    "allowed_file_types": list(self.settings.allowed_file_types),
                },
            )

        size = candidate.stat().st_size
        if size > self.settings.max_file_bytes:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_FILE_PATH,
                "File exceeds maximum allowed ingestion size.",
                {"path": relative_path, "size_bytes": size, "max_file_bytes": self.settings.max_file_bytes},
            )

        return candidate

    def _source_file_from_resolved_path(self, resolved_path: Path) -> str:
        project_root = self.settings.project_root.resolve()
        try:
            return resolved_path.resolve().relative_to(project_root).as_posix()
        except ValueError:
            return resolved_path.resolve().as_posix()

