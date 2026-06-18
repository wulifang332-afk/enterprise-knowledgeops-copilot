from __future__ import annotations

import shutil
from pathlib import Path

import pytest
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


def prepare_client(client: TestClient) -> None:
    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})
    assert ingest.status_code == 200
    graph = client.post("/api/v1/graph/rebuild")
    assert graph.status_code == 200


def test_query_api_returns_evidence_pack_not_final_answer(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    response = client.post(
        "/api/v1/query",
        json={
            "query": "Which approval form is required for vendor payments?",
            "top_k": 5,
            "include_graph": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["query"] == "Which approval form is required for vendor payments?"
    assert payload["intent"] == "policy_lookup"
    assert payload["route"] == "hybrid_retrieval_with_policy_filters"
    assert payload["status"] == "evidence_ready"
    assert payload["retrieval_evidence"]
    assert payload["graph_evidence"]["edges"]
    assert payload["citations"]
    assert payload["refusal_reason"] is None
    assert "Final answer generation is planned for Phase 5B." == payload["next_phase_note"]
    assert "answer" not in payload
    assert "final_answer" not in payload

    first = payload["retrieval_evidence"][0]
    assert first["citation"]["quote_hash"]
    assert first["citation"]["start_char"] < first["citation"]["end_char"]
    assert first["source_text_excerpt"]
    assert any(edge["evidence_quote"] for edge in payload["graph_evidence"]["edges"])


def test_query_api_graph_exploration_route(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    response = client.post("/api/v1/query", json={"query": "Show graph relationships for ServiceNow"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "graph_exploration"
    assert payload["route"] == "graph_neighborhood"
    assert payload["retrieval_evidence"] == []
    assert any(node["label"] == "ServiceNow" for node in payload["graph_evidence"]["matched_nodes"])


def test_query_api_process_system_graph_evidence(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    response = client.post("/api/v1/query", json={"query": "What system is used for Severity 1 incidents?"})

    assert response.status_code == 200
    payload = response.json()
    nodes = {
        node["node_id"]: node
        for node in [*payload["graph_evidence"]["matched_nodes"], *payload["graph_evidence"]["neighboring_nodes"]]
    }
    assert payload["intent"] == "process_lookup"
    assert any(node["label"] == "ServiceNow" for node in nodes.values())
    assert any(
        edge["relation_type"] == "USES_SYSTEM"
        and nodes.get(edge["target_node_id"], {}).get("label") == "ServiceNow"
        for edge in payload["graph_evidence"]["edges"]
    )
    assert "answer" not in payload
    assert "final_answer" not in payload


def test_query_api_structured_refusals(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    out_of_scope = client.post("/api/v1/query", json={"query": "What is the weather tomorrow?"})
    unsupported = client.post("/api/v1/query", json={"query": "Write the final answer for vendor approvals."})

    assert out_of_scope.status_code == 200
    out_payload = out_of_scope.json()
    assert out_payload["status"] == "refused"
    assert out_payload["refusal_reason"] == "OUT_OF_SCOPE"
    assert out_payload["retrieval_evidence"] == []

    assert unsupported.status_code == 200
    unsupported_payload = unsupported.json()
    assert unsupported_payload["status"] == "refused"
    assert unsupported_payload["refusal_reason"] == "UNSUPPORTED_IN_PHASE_5A"
    assert "Phase 5A" in " ".join(unsupported_payload["limitations"])


@pytest.mark.parametrize(
    "query",
    [
        "What is the capital of France?",
        "Who is the president of the United States?",
        "What is the weather in Singapore?",
        "Write a Python function to reverse a string.",
        "Tell me a joke.",
        "What is 2 + 2?",
    ],
)
def test_query_api_out_of_scope_enterprise_domain_gate(tmp_path: Path, query: str) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    response = client.post("/api/v1/query", json={"query": query})

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "out_of_scope"
    assert payload["route"] == "structured_refusal"
    assert payload["status"] == "refused"
    assert payload["refusal_reason"] == "OUT_OF_SCOPE"
    assert payload["retrieval_evidence"] == []
    assert payload["graph_evidence"]["edges"] == []
    assert "answer" not in payload
    assert "final_answer" not in payload


def test_query_api_existing_required_cross_border_query(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    response = client.post(
        "/api/v1/query",
        json={"query": "How does cross-border data approval work between APAC and EU?"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "multi_hop"
    assert payload["retrieval_evidence"]
    assert payload["graph_evidence"]["edges"]
    assert any(edge["source_doc_id"] == "cross-border-data-policy-v1-0" for edge in payload["graph_evidence"]["edges"][:10])


def test_query_api_rejects_malformed_filter_shapes(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post(
        "/api/v1/query",
        json={"query": "cross-border transfer approval", "filters": {"regions": "APAC"}},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert "errors" in payload["details"]
