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


def prepare_client(client: TestClient) -> None:
    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})
    assert ingest.status_code == 200
    graph = client.post("/api/v1/graph/rebuild")
    assert graph.status_code == 200


def test_phase6_evaluation_run_and_latest_contract(tmp_path: Path) -> None:
    client = make_client(tmp_path)
    prepare_client(client)

    run_response = client.post("/api/v1/evaluation/run")

    assert run_response.status_code == 200
    payload = run_response.json()
    assert payload["request_id"]
    report = payload["report"]
    assert report["dataset_version"] == "phase6-v1"
    assert report["total_cases"] == 22
    assert report["passed_cases"] == 22
    assert report["failed_cases"] == 0
    assert report["metrics"]["fabricated_answer_rate"] == 0.0
    assert report["split_metrics"]["core"]["total"] == 17
    assert report["split_metrics"]["holdout"]["total"] == 5
    assert "tmp" not in str(report).casefold()

    latest_response = client.get("/api/v1/evaluation/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["report"]["run_id"] == report["run_id"]


def test_phase6_evaluation_cases_contract(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/v1/evaluation/cases")

    assert response.status_code == 200
    payload = response.json()
    assert payload["request_id"]
    assert payload["dataset_version"] == "phase6-v1"
    assert payload["total_cases"] == 22
    assert len({item["case_id"] for item in payload["items"]}) == 22
    assert sum(item["split"] == "holdout" for item in payload["items"]) == 5


def test_phase6_latest_returns_structured_error_before_first_run(tmp_path: Path) -> None:
    client = make_client(tmp_path)

    response = client.get("/api/v1/evaluation/latest")

    assert response.status_code == 400
    payload = response.json()
    assert payload["error_code"] == "INVALID_REQUEST"
    assert payload["request_id"]
