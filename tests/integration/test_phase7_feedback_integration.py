from __future__ import annotations

import json
import shutil
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.evaluation.service import EvaluationService
from backend.app.feedback.schema import FeedbackCreateRequest
from backend.app.feedback.service import FeedbackService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "phase6_eval_cases.json"


def test_phase7_feedback_does_not_mutate_evaluation_dataset(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    dataset_dir = tmp_path / "evaluation" / "datasets"
    dataset_dir.mkdir(parents=True)
    dataset_path = dataset_dir / "phase6_eval_cases.json"
    shutil.copy2(DATASET_PATH, dataset_path)
    before = dataset_path.read_text(encoding="utf-8")
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)

    service = FeedbackService(settings)
    service.submit(
        FeedbackCreateRequest(
            query="Can this feedback become an evaluation case later?",
            user_rating="negative",
            feedback_type="answer_quality",
            issue_category="unsupported_answer",
            comment="Manual review should decide whether to curate this.",
            linked_eval_case_id="future_manual_case",
            source="manual",
        ),
        request_id="phase7-regression",
    )

    after = dataset_path.read_text(encoding="utf-8")
    loaded = EvaluationService(settings=settings, dataset_path=dataset_path).load_dataset()

    assert after == before
    assert len(loaded.cases) == 22
    assert (data_dir / "feedback" / "feedback.jsonl").exists()


def test_phase7_feedback_records_can_reference_query_context_without_changing_query_shape(tmp_path: Path) -> None:
    settings = AppSettings(project_root=tmp_path, data_dir=tmp_path / "data")
    service = FeedbackService(settings)
    record = service.submit(
        FeedbackCreateRequest(
            query="What is the capital of France?",
            request_id="query-request-1",
            intent="out_of_scope",
            route="structured_refusal",
            status="refused",
            answer_generation_status="refused",
            answer=None,
            user_rating="positive",
            feedback_type="refusal_issue",
            issue_category="other",
            comment="Refusal behaved as expected.",
            source="query_planner",
            metadata={"has_final_answer": False},
        ),
        request_id="feedback-api-request",
    )

    payload = json.loads((settings.feedback_dir / "feedback.jsonl").read_text(encoding="utf-8"))

    assert record.intent.value == "out_of_scope"
    assert payload["metadata"] == {"has_final_answer": False}
    assert "final_answer" not in payload
