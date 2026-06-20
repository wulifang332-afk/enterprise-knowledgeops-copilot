from __future__ import annotations

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.evaluation.service import EvaluationService
from backend.app.graph.service import GraphService
from backend.app.retrieval.indexing import IndexRebuildService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "phase6_eval_cases.json"


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    IndexRebuildService(settings).rebuild_all()
    GraphService(settings).rebuild()
    return settings


def test_phase6_runner_generates_deterministic_reports_and_artifacts(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = EvaluationService(settings=settings, dataset_path=DATASET_PATH)
    timestamp = datetime(2026, 6, 19, 0, 0, tzinfo=timezone.utc)

    first = service.run(run_id="deterministic-run", timestamp=timestamp, persist=True)
    second = service.run(run_id="deterministic-run", timestamp=timestamp, persist=False)

    assert first == second
    assert first.total_cases == 22
    assert first.passed_cases == 22
    assert first.failed_cases == 0
    assert first.metrics.fabricated_answer_rate == 0.0
    assert first.metrics.citation_validity_rate == 1.0
    assert service.latest_json_path.exists()
    assert service.latest_markdown_path.exists()
    assert (service.history_dir / "deterministic-run.json").exists()
    assert service.latest_report() == first
    assert first.split_metrics["core"].total == 17
    assert first.split_metrics["core"].pass_rate == 1.0
    assert first.split_metrics["holdout"].total == 5
    assert first.split_metrics["holdout"].pass_rate == 1.0
    assert any(result.split.value == "holdout" for result in first.per_case_results)
    assert "Holdout cases: 5/5 passed" in service.latest_markdown_path.read_text(encoding="utf-8")


def test_phase6_dashboard_executes_in_bare_python_mode() -> None:
    page = PROJECT_ROOT / "dashboard" / "pages" / "5_Evaluation_Dashboard.py"

    completed = subprocess.run(
        [sys.executable, str(page)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
