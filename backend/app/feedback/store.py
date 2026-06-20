from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from pydantic import ValidationError

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.feedback.schema import (
    FeedbackCreateRequest,
    FeedbackListFilters,
    FeedbackRecord,
    FeedbackSummary,
    FeedbackUpdateRequest,
    ReviewStatus,
    UserRating,
)
from backend.app.schemas.enums import ErrorCode


class FeedbackStore:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.settings.ensure_data_dirs()
        self.feedback_file = self.settings.feedback_dir / "feedback.jsonl"
        self.review_queue_file = self.settings.feedback_dir / "review_queue.json"
        self.corrupt_file = self.settings.feedback_dir / "feedback_corrupt.jsonl"

    def append(self, request: FeedbackCreateRequest) -> FeedbackRecord:
        record = FeedbackRecord(**request.model_dump())
        self._append_jsonl(self.feedback_file, record.model_dump(mode="json"))
        self._write_review_queue(self.list_all())
        return record

    def list_all(self) -> list[FeedbackRecord]:
        if not self.feedback_file.exists():
            return []
        records: list[FeedbackRecord] = []
        corrupt_entries: list[dict] = []
        with self.feedback_file.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if stripped:
                    try:
                        records.append(FeedbackRecord.model_validate(json.loads(stripped)))
                    except json.JSONDecodeError as exc:
                        corrupt_entries.append(self._corrupt_entry(line_number, stripped, "json_decode_error", exc))
                    except ValidationError as exc:
                        corrupt_entries.append(self._corrupt_entry(line_number, stripped, "validation_error", exc))
        self._write_corrupt_entries(corrupt_entries)
        return records

    def list_filtered(
        self,
        filters: FeedbackListFilters | None = None,
        *,
        offset: int = 0,
        limit: int = 100,
    ) -> tuple[list[FeedbackRecord], int, FeedbackSummary]:
        records = self._filter(self.list_all(), filters or FeedbackListFilters())
        summary = self.summarize(records)
        return records[offset : offset + limit], len(records), summary

    def get(self, feedback_id: str) -> FeedbackRecord:
        for record in self.list_all():
            if record.feedback_id == feedback_id:
                return record
        raise KnowledgeOpsError(
            ErrorCode.INVALID_REQUEST,
            "Feedback record not found.",
            {"feedback_id": feedback_id},
        )

    def update(self, feedback_id: str, request: FeedbackUpdateRequest) -> tuple[FeedbackRecord, list[str]]:
        records = self.list_all()
        changed_fields: list[str] = []
        updated_record: FeedbackRecord | None = None
        for index, record in enumerate(records):
            if record.feedback_id != feedback_id:
                continue
            update_data = request.model_dump(exclude_unset=True)
            for field_name, value in update_data.items():
                if getattr(record, field_name) != value:
                    setattr(record, field_name, value)
                    changed_fields.append(field_name)
            records[index] = record
            updated_record = record
            break
        if updated_record is None:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_REQUEST,
                "Feedback record not found.",
                {"feedback_id": feedback_id},
            )
        self._rewrite(records)
        self._write_review_queue(records)
        return updated_record, changed_fields

    @staticmethod
    def summarize(records: list[FeedbackRecord]) -> FeedbackSummary:
        issue_counts = Counter(record.issue_category.value for record in records)
        status_counts = Counter(record.review_status.value for record in records)
        type_counts = Counter(record.feedback_type.value for record in records)
        top_issues = [
            {"issue_category": issue, "count": count}
            for issue, count in issue_counts.most_common(5)
        ]
        unresolved_statuses = {ReviewStatus.OPEN, ReviewStatus.TRIAGED}
        return FeedbackSummary(
            total_count=len(records),
            negative_count=sum(record.user_rating == UserRating.NEGATIVE for record in records),
            unresolved_count=sum(record.review_status in unresolved_statuses for record in records),
            by_issue_category=dict(sorted(issue_counts.items())),
            by_review_status=dict(sorted(status_counts.items())),
            by_feedback_type=dict(sorted(type_counts.items())),
            top_issue_categories=top_issues,
        )

    @staticmethod
    def _filter(records: list[FeedbackRecord], filters: FeedbackListFilters) -> list[FeedbackRecord]:
        filtered = records
        if filters.review_status:
            filtered = [record for record in filtered if record.review_status == filters.review_status]
        if filters.feedback_type:
            filtered = [record for record in filtered if record.feedback_type == filters.feedback_type]
        if filters.issue_category:
            filtered = [record for record in filtered if record.issue_category == filters.issue_category]
        if filters.user_rating:
            filtered = [record for record in filtered if record.user_rating == filters.user_rating]
        return filtered

    @staticmethod
    def _append_jsonl(path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True) + "\n")

    def _rewrite(self, records: list[FeedbackRecord]) -> None:
        self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
        payload = "".join(
            json.dumps(record.model_dump(mode="json"), ensure_ascii=True, sort_keys=True) + "\n"
            for record in records
        )
        self._atomic_write_text(self.feedback_file, payload)

    def _write_review_queue(self, records: list[FeedbackRecord]) -> None:
        queue = [
            record.model_dump(mode="json")
            for record in records
            if record.review_status in {ReviewStatus.OPEN, ReviewStatus.TRIAGED}
        ]
        self.review_queue_file.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write_text(
            self.review_queue_file,
            json.dumps({"total": len(queue), "items": queue}, ensure_ascii=True, indent=2, sort_keys=True),
        )

    def _write_corrupt_entries(self, entries: list[dict]) -> None:
        if not entries:
            if self.corrupt_file.exists():
                self.corrupt_file.unlink()
            return
        payload = "".join(json.dumps(entry, ensure_ascii=True, sort_keys=True) + "\n" for entry in entries)
        self._atomic_write_text(self.corrupt_file, payload)

    @staticmethod
    def _corrupt_entry(line_number: int, raw_line: str, error_type: str, exc: Exception) -> dict:
        return {
            "line_number": line_number,
            "error_type": error_type,
            "error": str(exc)[:500],
            "raw_line": raw_line[:4000],
        }

    @staticmethod
    def _atomic_write_text(path: Path, payload: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
