from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_settings
from backend.app.core.settings import AppSettings
from backend.main import create_app


def make_client(tmp_path: Path) -> TestClient:
    settings = AppSettings(project_root=tmp_path, data_dir=tmp_path / "data")
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def feedback_payload(**overrides) -> dict:
    payload = {
        "query": "Which approval form is required for vendor payments?",
        "request_id": "query-req-1",
        "intent": "policy_lookup",
        "route": "hybrid_retrieval_with_policy_filters",
        "status": "evidence_ready",
        "answer_generation_status": "generated",
        "answer": "Vendor payments require the Vendor Payment Request Form.",
        "user_rating": "negative",
        "feedback_type": "citation_issue",
        "issue_category": "wrong_citation",
        "comment": "The citation preview did not show the required form.",
        "source": "query_planner",
        "metadata": {"test": True},
    }
    payload.update(overrides)
    return payload


def test_phase7_submit_list_read_and_patch_feedback_contract(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    created = client.post("/api/v1/feedback", json=feedback_payload())

    assert created.status_code == 200
    created_payload = created.json()
    assert created_payload["request_id"]
    feedback_id = created_payload["feedback_id"]
    assert feedback_id.startswith("fb:")
    assert created_payload["record"]["review_status"] == "open"

    listed = client.get("/api/v1/feedback", params={"user_rating": "negative"})
    assert listed.status_code == 200
    listed_payload = listed.json()
    assert listed_payload["total"] == 1
    assert listed_payload["summary"]["negative_count"] == 1
    assert listed_payload["items"][0]["feedback_id"] == feedback_id

    fetched = client.get(f"/api/v1/feedback/{feedback_id}")
    assert fetched.status_code == 200
    assert fetched.json()["record"]["feedback_id"] == feedback_id

    patched = client.patch(
        f"/api/v1/feedback/{feedback_id}",
        json={
            "review_status": "triaged",
            "reviewer_note": "Create a future evaluation case.",
            "linked_eval_case_id": "holdout_supplier_invoice_form",
        },
    )
    assert patched.status_code == 200
    patched_record = patched.json()["record"]
    assert patched_record["review_status"] == "triaged"
    assert patched_record["reviewer_note"] == "Create a future evaluation case."
    assert patched_record["linked_eval_case_id"] == "holdout_supplier_invoice_form"


def test_phase7_feedback_api_rejects_invalid_payload_and_id(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    bad_payload = client.post("/api/v1/feedback", json=feedback_payload(user_rating="bad"))
    assert bad_payload.status_code == 422
    assert bad_payload.json()["error_code"] == "INVALID_REQUEST"
    assert bad_payload.json()["request_id"]

    missing = client.get("/api/v1/feedback/fb:not-found")
    assert missing.status_code == 400
    assert missing.json()["error_code"] == "INVALID_REQUEST"
    assert missing.json()["details"] == {"feedback_id": "fb:not-found"}


def test_phase7_feedback_api_audit_events_created(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    created = client.post("/api/v1/feedback", json=feedback_payload())
    feedback_id = created.json()["feedback_id"]

    client.patch(f"/api/v1/feedback/{feedback_id}", json={"review_status": "resolved"})

    audit_file = tmp_path / "data" / "audit" / "audit.jsonl"
    lines = audit_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "feedback_submission" in lines[0]
    assert "feedback_status_updated" in lines[1]
    assert feedback_id in lines[0]
    assert feedback_id in lines[1]
