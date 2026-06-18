from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from backend.app.audit.logger import AuditLogger
from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.repositories.sqlite import SQLiteRepository
from backend.app.schemas.documents import Document
from backend.app.schemas.enums import AuditEventType, ErrorCode, IngestionStatus
from backend.app.schemas.operational import IngestionFileResult, IngestionSummary

from .chunker import ChunkingService
from .loader import DocumentLoader
from .metadata import MetadataParser
from .sections import SectionParser
from .utils import utc_now


class IngestionService:
    def __init__(
        self,
        settings: AppSettings | None = None,
        repository: SQLiteRepository | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> None:
        self.settings = settings or AppSettings()
        self.settings.ensure_data_dirs()
        self.loader = DocumentLoader(self.settings)
        self.metadata_parser = MetadataParser()
        self.section_parser = SectionParser()
        self.chunker = ChunkingService(self.settings)
        self.repository = repository or SQLiteRepository(self.settings)
        self.audit_logger = audit_logger or AuditLogger(self.settings)

    def ingest_all_raw(self, *, request_id: str | None = None) -> IngestionSummary:
        return self.ingest_paths(self.loader.list_raw_files(), request_id=request_id)

    def ingest_paths(self, paths: list[str], *, request_id: str | None = None) -> IngestionSummary:
        request_id = request_id or str(uuid4())
        summary = IngestionSummary(request_id=request_id, total_files=len(paths))
        for path in paths:
            result = self._ingest_one(path, request_id=request_id)
            summary.results.append(result)
            if result.status == IngestionStatus.INGESTED:
                summary.ingested_count += 1
            elif result.status == IngestionStatus.SKIPPED:
                summary.skipped_count += 1
            else:
                summary.failed_count += 1
        return summary

    def _ingest_one(self, path: str, *, request_id: str) -> IngestionFileResult:
        started = perf_counter()
        try:
            _, source_file, normalized_text = self.loader.load_relative_file(path)
            parsed = self.metadata_parser.parse(
                normalized_text=normalized_text,
                source_file=source_file,
            )

            existing_hash = self.repository.get_document_content_hash(parsed.metadata.doc_id)
            if existing_hash == parsed.metadata.content_sha256:
                result = IngestionFileResult(
                    source_file=source_file,
                    status=IngestionStatus.SKIPPED,
                    doc_id=parsed.metadata.doc_id,
                    content_sha256=parsed.metadata.content_sha256,
                    message="Document already ingested with identical content hash.",
                )
                self.audit_logger.write(
                    event_type=AuditEventType.DOCUMENT_INGESTION,
                    request_id=request_id,
                    outcome="skipped",
                    resource_ids=[parsed.metadata.doc_id],
                    details={"source_file": source_file},
                    duration_ms=self._elapsed_ms(started),
                )
                return result
            if existing_hash and existing_hash != parsed.metadata.content_sha256:
                raise KnowledgeOpsError(
                    ErrorCode.DUPLICATE_DOCUMENT,
                    "A document with this doc_id already exists with different content.",
                    {"doc_id": parsed.metadata.doc_id, "source_file": source_file},
                )

            sections = self.section_parser.parse(doc_id=parsed.metadata.doc_id, content=parsed.content)
            chunks = self.chunker.chunk_document(metadata=parsed.metadata, sections=sections)
            document = Document(
                metadata=parsed.metadata,
                content=parsed.content,
                sections=sections,
                chunks=chunks,
                ingested_at=utc_now(),
            )
            self.repository.upsert_document(document)
            self._write_processed_document(document)
            result = IngestionFileResult(
                source_file=source_file,
                status=IngestionStatus.INGESTED,
                doc_id=parsed.metadata.doc_id,
                content_sha256=parsed.metadata.content_sha256,
                chunk_count=len(chunks),
                section_count=len(sections),
                message="Document ingested successfully.",
            )
            self.audit_logger.write(
                event_type=AuditEventType.DOCUMENT_INGESTION,
                request_id=request_id,
                outcome="success",
                resource_ids=[parsed.metadata.doc_id],
                details={
                    "source_file": source_file,
                    "chunk_count": len(chunks),
                    "section_count": len(sections),
                },
                duration_ms=self._elapsed_ms(started),
            )
            return result
        except KnowledgeOpsError as exc:
            safe_source = path if not path.startswith("/") else "<absolute-path-rejected>"
            self.audit_logger.write(
                event_type=AuditEventType.DOCUMENT_VALIDATION_FAILURE,
                request_id=request_id,
                outcome="failure",
                details={"source_file": safe_source, **exc.details},
                error_code=exc.error_code,
                duration_ms=self._elapsed_ms(started),
            )
            return IngestionFileResult(
                source_file=safe_source,
                status=IngestionStatus.FAILED,
                error_code=exc.error_code,
                message=exc.message,
            )

    def _write_processed_document(self, document: Document) -> None:
        output_path = self.settings.processed_dir / f"{document.metadata.doc_id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = document.model_dump(mode="json")
        existing_ingested_at = self._existing_processed_ingested_at(
            output_path=output_path,
            content_sha256=document.metadata.content_sha256,
        )
        if existing_ingested_at:
            payload["ingested_at"] = existing_ingested_at
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
            handle.write("\n")

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((perf_counter() - started) * 1000)

    @staticmethod
    def _existing_processed_ingested_at(*, output_path: Path, content_sha256: str) -> str | None:
        try:
            with open(output_path, encoding="utf-8") as handle:
                existing = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        if existing.get("metadata", {}).get("content_sha256") != content_sha256:
            return None
        ingested_at = existing.get("ingested_at")
        return ingested_at if isinstance(ingested_at, str) and ingested_at else None
