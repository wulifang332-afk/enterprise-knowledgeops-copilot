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
    dataset_dir = tmp_path / "evaluation" / "datasets"
    dataset_dir.mkdir(parents=True)
    shutil.copy2(
        PROJECT_ROOT / "evaluation" / "datasets" / "phase6_eval_cases.json",
        dataset_dir / "phase6_eval_cases.json",
    )
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def test_workspace_summary_counts_processed_documents_chunks_and_graph(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": False})
    assert ingest.status_code == 200
    rebuild = client.post("/api/v1/graph/rebuild")
    assert rebuild.status_code == 200

    response = client.get("/api/v1/workspace/summary")

    assert response.status_code == 200
    assert response.json() == {
        "documents": 8,
        "chunks": 40,
        "graph_nodes": 96,
        "graph_edges": 207,
    }


def test_workspace_summary_returns_zero_graph_counts_before_graph_rebuild(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": False})
    assert ingest.status_code == 200

    response = client.get("/api/v1/workspace/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["documents"] == 8
    assert payload["chunks"] == 40
    assert payload["graph_nodes"] == 0
    assert payload["graph_edges"] == 0


def test_evaluation_summary_reports_unavailable_before_first_run(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/v1/evaluation/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is False
    assert payload["run_id"] is None
    assert payload["total_cases"] == 0
    assert payload["pass_rate"] is None
    assert payload["core_total"] == 0
    assert payload["holdout_total"] == 0


def test_evaluation_summary_aggregates_latest_report_artifact(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})
    assert ingest.status_code == 200
    graph = client.post("/api/v1/graph/rebuild")
    assert graph.status_code == 200
    run = client.post("/api/v1/evaluation/run")
    assert run.status_code == 200
    report = run.json()["report"]

    response = client.get("/api/v1/evaluation/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["run_id"] == report["run_id"]
    assert payload["dataset_version"] == "phase6-v1"
    assert payload["total_cases"] == 22
    assert payload["passed_cases"] == 22
    assert payload["failed_cases"] == 0
    assert payload["pass_rate"] == 1.0
    assert payload["intent_accuracy"] == 1.0
    assert payload["route_accuracy"] == 1.0
    assert payload["citation_validity_rate"] == 1.0
    assert payload["grounded_answer_pass_rate"] == 1.0
    assert payload["fabricated_answer_rate"] == 0.0
    assert payload["core_total"] == 17
    assert payload["core_passed"] == 17
    assert payload["holdout_total"] == 5
    assert payload["holdout_passed"] == 5
