from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_settings
from backend.app.core.settings import AppSettings
from backend.app.retrieval.indexing import IndexRebuildService
from backend.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_client(tmp_path: Path | None = None, *, indexed: bool = False) -> TestClient:
    app = create_app()
    if tmp_path is not None:
        data_dir = tmp_path / "data"
        if indexed:
            shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
        settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
        if indexed:
            IndexRebuildService(settings).rebuild_all()
        app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_phase9b_personas_endpoint_contract() -> None:
    client = make_client()

    response = client.get("/api/v1/readiness/personas")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert [item["persona_id"] for item in payload["items"]] == [
        "global_admin",
        "finance_manager_apac",
        "hr_manager_eu",
        "it_support_internal",
        "legal_reviewer_global",
        "employee_public",
    ]
    first = payload["items"][0]
    assert set(first) == {
        "persona_id",
        "display_name",
        "department",
        "regions",
        "max_access_level",
        "allowed_policy_types",
        "description",
    }


def test_phase9b_access_policy_endpoint_contract() -> None:
    client = make_client()

    response = client.post(
        "/api/v1/readiness/access-policy",
        json={
            "persona_id": "hr_manager_eu",
            "requested_departments": ["Human Resources", "Finance"],
            "requested_regions": ["EU", "APAC"],
            "requested_policy_types": ["policy", "standard"],
            "requested_access_levels": ["internal", "confidential"],
            "requested_owners": ["Human Resources Operations", "Finance Operations"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["simulation_only"] is True
    assert payload["persona"]["persona_id"] == "hr_manager_eu"
    assert payload["allowed_filters"] == {
        "departments": ["Human Resources"],
        "regions": ["EU"],
        "policy_types": ["policy"],
        "access_levels": ["internal"],
        "owners": ["Human Resources Operations"],
    }
    assert payload["denied_reasons"] == [
        "requested_departments denied outside persona scope: Finance",
        "requested_regions denied outside persona scope: APAC",
        "requested_policy_types denied outside persona scope: standard",
        "requested_access_levels denied above max_access_level restricted: confidential",
        "requested_owners denied outside persona scope: Finance Operations",
    ]
    assert "simulation-only" in payload["explanation"]


def test_phase9b_access_policy_unknown_persona_returns_clean_error() -> None:
    client = make_client()

    response = client.post("/api/v1/readiness/access-policy", json={"persona_id": "not_real"})

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["message"] == "Unknown simulated persona."
    assert payload["details"] == {"persona_id": "not_real"}
    assert payload["request_id"]


def test_phase9b_readiness_summary_endpoint_contract_handles_missing_artifacts(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["simulation_only"] is True
    assert payload["personas_count"] == 6
    assert payload["access_levels"] == ["public", "internal", "restricted", "confidential"]
    assert payload["readiness_capabilities"] == {
        "access_policy_simulation": True,
        "metadata_filter_generation": True,
        "persona_explanations": True,
        "local_first": True,
    }
    assert payload["corpus_metadata_distributions"] == {
        "departments": {},
        "regions": {},
        "policy_types": {},
        "owners": {},
        "access_levels": {},
    }
    assert payload["graph_status"] == {"available": False, "node_count": 0, "edge_count": 0}
    assert payload["evaluation_status"] == {
        "available": False,
        "total_cases": 0,
        "passed_cases": 0,
        "pass_rate": None,
    }
    assert payload["governance_status"] == {
        "available": False,
        "feedback_count": 0,
        "review_status_breakdown": {},
    }
    assert payload["non_goals"] == [
        "no real auth",
        "no SSO",
        "no production RBAC",
        "no production infra",
    ]


def test_phase9b_readiness_summary_reports_corpus_metadata_distributions(tmp_path: Path) -> None:
    client = make_client(tmp_path, indexed=True)

    response = client.get("/api/v1/readiness/summary")

    assert response.status_code == 200
    distributions = response.json()["corpus_metadata_distributions"]
    assert distributions["departments"] == {
        "Customer Operations": 1,
        "Finance": 2,
        "Human Resources": 2,
        "IT": 1,
        "Information Security": 1,
        "Legal and Compliance": 1,
    }
    assert distributions["regions"] == {"APAC": 1, "EU": 1, "Global": 7}
    assert distributions["policy_types"] == {"policy": 5, "sop": 3}
    assert distributions["access_levels"] == {"confidential": 1, "internal": 5, "restricted": 2}


def test_phase9b_search_default_behavior_does_not_require_access_policy(tmp_path: Path) -> None:
    client = make_client(tmp_path, indexed=True)

    response = client.post(
        "/api/v1/search",
        json={
            "query": "Which approval form is required for vendor payments?",
            "top_k": 5,
            "retrieval_mode": "hybrid",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["results"]
    assert any(result["doc_id"] == "vendor-payment-approval-policy-v1-0" for result in payload["results"])


def test_phase9b_query_default_behavior_does_not_require_access_policy(tmp_path: Path) -> None:
    client = make_client(tmp_path, indexed=True)

    response = client.post(
        "/api/v1/query",
        json={
            "query": "Which approval form is required for vendor payments?",
            "top_k": 5,
            "include_graph": False,
            "generate_answer": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "policy_lookup"
    assert payload["route"] == "hybrid_retrieval_with_policy_filters"
    assert payload["retrieval_evidence"]
    assert payload["answer"] is None
