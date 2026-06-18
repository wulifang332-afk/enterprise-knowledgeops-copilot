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


def test_graph_api_rebuild_nodes_edges_and_neighborhood_contract(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": False})
    assert ingest.status_code == 200

    rebuild = client.post("/api/v1/graph/rebuild")
    assert rebuild.status_code == 200
    rebuild_payload = rebuild.json()
    assert rebuild_payload["request_id"]
    assert rebuild_payload["node_count"] > 0
    assert rebuild_payload["edge_count"] > 0
    assert rebuild_payload["source_chunk_count"] == 40

    nodes = client.get("/api/v1/graph/nodes", params={"label_contains": "ServiceNow"})
    assert nodes.status_code == 200
    nodes_payload = nodes.json()
    assert nodes_payload["request_id"]
    assert nodes_payload["items"]
    servicenow = next(node for node in nodes_payload["items"] if node["label"] == "ServiceNow")
    for field in ("node_id", "label", "type", "source_doc_ids", "source_chunk_ids", "mentions", "confidence", "created_by"):
        assert field in servicenow

    edges = client.get("/api/v1/graph/edges", params={"relation_type": "USES_SYSTEM"})
    assert edges.status_code == 200
    edges_payload = edges.json()
    assert edges_payload["request_id"]
    assert edges_payload["items"]
    assert any(edge["target_node_id"] == servicenow["node_id"] for edge in edges_payload["items"])
    first_edge = edges_payload["items"][0]
    for field in (
        "edge_id",
        "source_node_id",
        "target_node_id",
        "relation_type",
        "source_doc_id",
        "source_chunk_id",
        "evidence_quote",
        "confidence",
        "created_by",
    ):
        assert field in first_edge

    neighborhood = client.get(
        "/api/v1/graph/neighborhood",
        params={"node_id": servicenow["node_id"], "depth": 1},
    )
    assert neighborhood.status_code == 200
    neighborhood_payload = neighborhood.json()
    assert neighborhood_payload["selected_node"]["label"] == "ServiceNow"
    assert neighborhood_payload["nodes"]
    assert neighborhood_payload["edges"]


def test_graph_neighborhood_rejects_depth_above_limit(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": False})
    client.post("/api/v1/graph/rebuild")
    nodes = client.get("/api/v1/graph/nodes", params={"label_contains": "ServiceNow"}).json()
    servicenow = next(node for node in nodes["items"] if node["label"] == "ServiceNow")

    response = client.get("/api/v1/graph/neighborhood", params={"node_id": servicenow["node_id"], "depth": 3})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
    assert "errors" in payload["details"]


def test_query_endpoint_remains_absent_after_phase4(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.post("/api/v1/query", json={"query": "Who approves vendor payments?"})

    assert response.status_code == 404
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
