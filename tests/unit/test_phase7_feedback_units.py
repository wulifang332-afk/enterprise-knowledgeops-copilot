from __future__ import annotations

import json
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.feedback.schema import (
    FeedbackCreateRequest,
    FeedbackListFilters,
    FeedbackRecord,
    FeedbackType,
    FeedbackUpdateRequest,
    IssueCategory,
    ReviewStatus,
    UserRating,
)
from backend.app.feedback.service import FeedbackService
from backend.app.feedback.store import FeedbackStore
from dashboard.feedback_summary import summarize_feedback

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_settings(tmp_path: Path) -> AppSettings:
    return AppSettings(project_root=tmp_path, data_dir=tmp_path / "data")


def feedback_request(**overrides) -> FeedbackCreateRequest:
    payload = {
        "query": "Which approval form is required for vendor payments?",
        "request_id": "req-123",
        "user_rating": UserRating.NEGATIVE,
        "feedback_type": FeedbackType.CITATION_ISSUE,
        "issue_category": IssueCategory.WRONG_CITATION,
        "comment": "The citation did not support the displayed form.",
        "source": "api",
    }
    payload.update(overrides)
    return FeedbackCreateRequest(**payload)


def test_phase7_feedback_schema_accepts_valid_record() -> None:
    record = FeedbackRecord(**feedback_request().model_dump())

    assert record.feedback_id.startswith("fb:")
    assert record.review_status == ReviewStatus.OPEN
    assert record.user_rating == UserRating.NEGATIVE
    assert record.feedback_type == FeedbackType.CITATION_ISSUE


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("user_rating", "bad"),
        ("feedback_type", "bad"),
        ("issue_category", "bad"),
    ],
)
def test_phase7_feedback_schema_rejects_invalid_enums(field_name: str, value: str) -> None:
    with pytest.raises(ValidationError):
        feedback_request(**{field_name: value})


def test_phase7_feedback_schema_enforces_required_fields() -> None:
    with pytest.raises(ValidationError):
        FeedbackCreateRequest(
            query="Which approval form is required for vendor payments?",
            user_rating=UserRating.NEGATIVE,
            feedback_type=FeedbackType.ANSWER_QUALITY,
            issue_category=IssueCategory.UNSUPPORTED_ANSWER,
        )


def test_phase7_feedback_store_append_list_filter_and_update(tmp_path: Path) -> None:
    store = FeedbackStore(make_settings(tmp_path))
    first = store.append(feedback_request())
    second = store.append(
        feedback_request(
            query="What system is used for Severity 1 incidents?",
            user_rating=UserRating.POSITIVE,
            feedback_type=FeedbackType.ANSWER_QUALITY,
            issue_category=IssueCategory.OTHER,
            comment="Looks grounded.",
        )
    )

    items, total, summary = store.list_filtered()
    assert total == 2
    assert [item.feedback_id for item in items] == [first.feedback_id, second.feedback_id]
    assert summary.negative_count == 1
    assert summary.unresolved_count == 2

    filtered, filtered_total, _ = store.list_filtered(FeedbackListFilters(user_rating=UserRating.NEGATIVE))
    assert filtered_total == 1
    assert filtered[0].feedback_id == first.feedback_id

    updated, changed = store.update(
        first.feedback_id,
        FeedbackUpdateRequest(
            review_status=ReviewStatus.TRIAGED,
            reviewer_note="Needs citation review.",
            linked_eval_case_id="core_vendor_form",
        ),
    )
    assert set(changed) == {"review_status", "reviewer_note", "linked_eval_case_id"}
    assert updated.review_status == ReviewStatus.TRIAGED
    assert updated.reviewer_note == "Needs citation review."
    assert "Needs citation review." in store.feedback_file.read_text(encoding="utf-8")
    assert not store.feedback_file.with_name(f".{store.feedback_file.name}.tmp").exists()
    assert store.review_queue_file.exists()
    queue = json.loads(store.review_queue_file.read_text(encoding="utf-8"))
    assert queue["total"] == 2


def test_phase7_feedback_store_skips_and_quarantines_malformed_jsonl(tmp_path: Path) -> None:
    store = FeedbackStore(make_settings(tmp_path))
    first = FeedbackRecord(**feedback_request(query="First valid feedback").model_dump())
    second = FeedbackRecord(**feedback_request(query="Second valid feedback").model_dump())
    invalid_schema = {
        "feedback_id": "fb:schema-invalid",
        "query": "Missing required enum fields",
        "comment": "This line is not a valid FeedbackRecord.",
    }
    store.feedback_file.parent.mkdir(parents=True, exist_ok=True)
    store.feedback_file.write_text(
        "\n".join(
            [
                json.dumps(first.model_dump(mode="json"), sort_keys=True),
                "{malformed-json",
                json.dumps(invalid_schema, sort_keys=True),
                json.dumps(second.model_dump(mode="json"), sort_keys=True),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    records = store.list_all()

    assert [record.query for record in records] == ["First valid feedback", "Second valid feedback"]
    corrupt_lines = store.corrupt_file.read_text(encoding="utf-8").splitlines()
    assert len(corrupt_lines) == 2
    corrupt_entries = [json.loads(line) for line in corrupt_lines]
    assert [entry["error_type"] for entry in corrupt_entries] == ["json_decode_error", "validation_error"]
    assert [entry["line_number"] for entry in corrupt_entries] == [2, 3]


def test_phase7_feedback_store_valid_records_clear_corrupt_quarantine(tmp_path: Path) -> None:
    store = FeedbackStore(make_settings(tmp_path))
    store.corrupt_file.parent.mkdir(parents=True, exist_ok=True)
    store.corrupt_file.write_text("stale corrupt note\n", encoding="utf-8")
    store.append(feedback_request())

    records = store.list_all()

    assert len(records) == 1
    assert not store.corrupt_file.exists()


def test_phase7_feedback_store_invalid_id_raises_structured_error(tmp_path: Path) -> None:
    store = FeedbackStore(make_settings(tmp_path))

    with pytest.raises(KnowledgeOpsError) as exc_info:
        store.get("fb:not-found")

    assert exc_info.value.error_code.value == "INVALID_REQUEST"
    assert exc_info.value.details == {"feedback_id": "fb:not-found"}


def test_phase7_feedback_service_writes_audit_events(tmp_path: Path) -> None:
    service = FeedbackService(make_settings(tmp_path))
    record = service.submit(feedback_request(), request_id="api-req-1")

    service.update(
        record.feedback_id,
        FeedbackUpdateRequest(review_status=ReviewStatus.TRIAGED, reviewer_note="Triage note."),
        request_id="api-req-2",
    )

    audit_lines = (tmp_path / "data" / "audit" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in audit_lines]
    assert [event["event_type"] for event in events] == [
        "feedback_submission",
        "feedback_status_updated",
        "feedback_reviewer_note_updated",
    ]
    assert all(event["feedback_id"] == record.feedback_id for event in events)
    assert events[0]["summary"] == "Feedback submitted."


def test_phase7_feedback_summary_handles_empty_and_sample_records() -> None:
    assert summarize_feedback([])["total_count"] == 0

    summary = summarize_feedback(
        [
            {
                "user_rating": "negative",
                "review_status": "open",
                "issue_category": "wrong_citation",
                "feedback_type": "citation_issue",
            },
            {
                "user_rating": "neutral",
                "review_status": "resolved",
                "issue_category": "wrong_citation",
                "feedback_type": "answer_quality",
            },
        ]
    )

    assert summary["total_count"] == 2
    assert summary["negative_count"] == 1
    assert summary["unresolved_count"] == 1
    assert summary["top_issue_categories"][0] == {"issue_category": "wrong_citation", "count": 2}


def test_phase7_feedback_generated_artifacts_are_gitignored() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    generated_feedback_files = {"feedback.jsonl", "review_queue.json", "feedback_corrupt.jsonl"}

    assert "data/feedback/*" in gitignore
    assert "!data/feedback/.gitkeep" in gitignore
    assert all(fnmatch(f"data/feedback/{name}", "data/feedback/*") for name in generated_feedback_files)


def test_phase7_feedback_dashboard_executes_in_bare_python_mode() -> None:
    page = PROJECT_ROOT / "dashboard" / "pages" / "6_Feedback_Governance.py"

    completed = subprocess.run(
        [sys.executable, str(page)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
