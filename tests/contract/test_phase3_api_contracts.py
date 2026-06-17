from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_settings
from backend.app.core.settings import AppSettings
from backend.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_client(tmp_path: Path) -> TestClient:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "raw", data_dir / "raw")
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_ingest_documents_chunks_and_search_contracts(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    ingest_response = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})
    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["request_id"]
    assert ingest_payload["total_files"] == 8
    assert ingest_payload["failed_count"] == 0
    assert ingest_payload["index_rebuild"]["succeeded"] is True

    documents_response = client.get("/api/v1/documents", params={"department": "Finance", "limit": 10})
    assert documents_response.status_code == 200
    documents_payload = documents_response.json()
    assert documents_payload["request_id"]
    assert documents_payload["total"] == 2
    assert {"metadata", "chunk_count", "section_count"}.issubset(documents_payload["items"][0])

    chunks_response = client.get(
        "/api/v1/chunks",
        params={"doc_id": "vendor-payment-approval-policy-v1-0", "section_title": "Approval"},
    )
    assert chunks_response.status_code == 200
    chunks_payload = chunks_response.json()
    assert chunks_payload["request_id"]
    assert chunks_payload["total"] >= 1
    first_chunk = chunks_payload["items"][0]
    assert {"metadata", "start_char", "end_char", "text_sha256", "text"}.issubset(first_chunk)

    search_response = client.post(
        "/api/v1/search",
        json={
            "query": "Vendor Payment Request Form",
            "retrieval_mode": "bm25",
            "top_k": 3,
            "filters": {},
        },
    )
    assert search_response.status_code == 200
    search_payload = search_response.json()
    assert search_payload["request_id"]
    assert search_payload["retrieval_mode"] == "bm25"
    assert search_payload["results"]
    citation = search_payload["results"][0]["citation"]
    for field in (
        "citation_id",
        "doc_id",
        "chunk_id",
        "title",
        "section_title",
        "source_file",
        "version",
        "effective_date",
        "quote",
        "start_char",
        "end_char",
        "quote_hash",
    ):
        assert field in citation


def test_invalid_request_returns_structured_error_with_request_id(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    response = client.post(
        "/api/v1/search",
        json={"query": "x", "retrieval_mode": "invalid", "top_k": 999, "filters": {}},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
    assert payload["timestamp"]
    assert "errors" in payload["details"]
    assert response.headers["X-Request-ID"] == payload["request_id"]


def test_search_rejects_malformed_filter_shapes(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})

    response = client.post(
        "/api/v1/search",
        json={
            "query": "cross-border transfer approval",
            "retrieval_mode": "hybrid",
            "top_k": 5,
            "filters": {"regions": "APAC"},
        },
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
    assert "errors" in payload["details"]


def test_search_accepts_valid_typed_filters(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})

    response = client.post(
        "/api/v1/search",
        json={
            "query": "cross-border transfer approval",
            "retrieval_mode": "hybrid",
            "top_k": 5,
            "filters": {
                "regions": ["APAC"],
                "policy_types": ["policy"],
                "section_titles": ["Approval"],
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert all("APAC" in result["metadata"]["regions"] for result in payload["results"])
    assert all("Approval" in result["metadata"]["section_title"] for result in payload["results"])


def test_ingest_with_files_ingests_only_selected_files_even_when_ingest_all_default_true(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/ingest",
        json={"files": ["hr_leave_policy.md"], "rebuild_indexes": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_files"] == 1
    assert payload["failed_count"] == 0
    assert payload["results"][0]["doc_id"] == "hr-leave-policy-v1-0"

    documents = client.get("/api/v1/documents", params={"limit": 20}).json()
    assert documents["total"] == 1
    assert documents["items"][0]["metadata"]["doc_id"] == "hr-leave-policy-v1-0"


def test_ingest_with_no_files_and_ingest_all_false_returns_structured_invalid_request(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/ingest",
        json={"files": [], "ingest_all": False, "rebuild_indexes": False},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
    assert payload["message"] == "Provide at least one file or set ingest_all=true."


def test_ingest_rejects_unsafe_paths_through_api_layer(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/ingest",
        json={"files": ["../outside.md"], "rebuild_indexes": False},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["failed_count"] == 1
    assert payload["results"][0]["status"] == "failed"
    assert payload["results"][0]["error_code"] == "INVALID_FILE_PATH"


def test_query_endpoint_is_not_implemented_in_phase3(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post("/api/v1/query", json={"query": "Who approves vendor payments?"})

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
