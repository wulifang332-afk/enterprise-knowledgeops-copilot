from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from pydantic import ValidationError

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.query.schema import QueryRequest
from backend.app.query.service import QueryPlanningService
from backend.app.schemas.enums import ErrorCode

from .metrics import aggregate_metrics, aggregate_split_metrics, evaluate_case
from .schema import EvaluationCase, EvaluationDataset, EvaluationReport

DEFAULT_DATASET_RELATIVE_PATH = Path("evaluation/datasets/phase6_eval_cases.json")
REPORT_LIMITATIONS = [
    "Metrics are deterministic checks over a synthetic enterprise corpus.",
    "Retrieval and citation checks do not establish semantic answer faithfulness.",
    "No LLM-as-a-judge, human feedback loop, production monitoring, or online experimentation is used.",
]


class EvaluationService:
    def __init__(self, settings: AppSettings, dataset_path: Path | None = None) -> None:
        self.settings = settings
        self.dataset_path = dataset_path or settings.project_root / DEFAULT_DATASET_RELATIVE_PATH
        self.query_service = QueryPlanningService(settings)

    @property
    def report_dir(self) -> Path:
        return self.settings.evaluation_dir

    @property
    def latest_json_path(self) -> Path:
        return self.report_dir / "latest_report.json"

    @property
    def latest_markdown_path(self) -> Path:
        return self.report_dir / "latest_report.md"

    @property
    def history_dir(self) -> Path:
        return self.report_dir / "history"

    def load_dataset(self) -> EvaluationDataset:
        if not self.dataset_path.exists():
            raise KnowledgeOpsError(
                ErrorCode.INVALID_EVALUATION_CASE,
                "Phase 6 evaluation dataset is unavailable.",
                {"dataset": self.dataset_path.name},
            )
        try:
            payload = json.loads(self.dataset_path.read_text(encoding="utf-8"))
            return EvaluationDataset.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_EVALUATION_CASE,
                "Phase 6 evaluation dataset is invalid.",
                {"reason": str(exc)},
            ) from exc

    def list_cases(self) -> EvaluationDataset:
        return self.load_dataset()

    def run(
        self,
        *,
        run_id: str | None = None,
        timestamp: datetime | None = None,
        persist: bool = True,
    ) -> EvaluationReport:
        self.ensure_preconditions()
        dataset = self.load_dataset()
        timestamp = normalize_timestamp(timestamp or datetime.now(timezone.utc))
        run_id = run_id or f"phase6-{timestamp.strftime('%Y%m%dT%H%M%SZ')}"

        results = []
        for case in dataset.cases:
            pack = self.query_service.plan(
                request=QueryRequest(
                    query=case.query,
                    top_k=case.top_k,
                    include_graph=case.include_graph,
                    generate_answer=case.generate_answer,
                ),
                request_id=f"evaluation:{case.case_id}",
            )
            results.append(evaluate_case(case, pack))

        metrics, intent_metrics, confusion = aggregate_metrics(dataset.cases, results)
        split_metrics = aggregate_split_metrics(dataset.cases, results)
        failures = [result for result in results if not result.passed]
        report = EvaluationReport(
            run_id=run_id,
            timestamp=timestamp,
            dataset_version=dataset.dataset_version,
            total_cases=len(results),
            passed_cases=len(results) - len(failures),
            failed_cases=len(failures),
            metrics=metrics,
            split_metrics=split_metrics,
            per_intent_metrics=intent_metrics,
            intent_confusion_summary=confusion,
            per_case_results=results,
            failures=failures,
            limitations=REPORT_LIMITATIONS,
        )
        if persist:
            self.persist_report(report)
        return report

    def latest_report(self) -> EvaluationReport:
        if not self.latest_json_path.exists():
            raise KnowledgeOpsError(
                ErrorCode.INVALID_REQUEST,
                "No Phase 6 evaluation report is available. Run the evaluation first.",
            )
        try:
            payload = json.loads(self.latest_json_path.read_text(encoding="utf-8"))
            return EvaluationReport.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_EVALUATION_CASE,
                "The latest Phase 6 evaluation report is invalid.",
                {"reason": str(exc)},
            ) from exc

    def ensure_preconditions(self) -> None:
        missing = []
        if not (self.settings.bm25_index_dir / "index.json").exists():
            missing.append("BM25 index")
        if (
            not (self.settings.indexes_dir / "chroma_manifest.json").exists()
            or not self.settings.chroma_index_dir.exists()
        ):
            missing.append("Chroma index")
        if not (self.settings.graph_dir / "knowledge_graph.json").exists():
            missing.append("knowledge graph")
        if missing:
            raise KnowledgeOpsError(
                ErrorCode.INDEX_UNAVAILABLE,
                "Phase 6 evaluation preconditions are not satisfied.",
                {
                    "missing": missing,
                    "remediation": "Run scripts/rebuild_indexes.py and scripts/rebuild_graph.py.",
                },
            )

    def persist_report(self, report: EvaluationReport) -> None:
        self.history_dir.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True)
        markdown = render_markdown_report(report)
        atomic_write(self.latest_json_path, payload)
        atomic_write(self.latest_markdown_path, markdown)
        history_name = f"{safe_filename(report.run_id)}.json"
        atomic_write(self.history_dir / history_name, payload)


def render_markdown_report(report: EvaluationReport) -> str:
    metrics = report.metrics
    lines = [
        "# Phase 6 Evaluation Report",
        "",
        f"- Run ID: `{report.run_id}`",
        f"- Timestamp: `{report.timestamp.isoformat()}`",
        f"- Dataset: `{report.dataset_version}`",
        f"- Cases: {report.passed_cases}/{report.total_cases} passed",
        f"- Core cases: {report.split_metrics['core'].passed}/{report.split_metrics['core'].total} passed",
        f"- Holdout cases: {report.split_metrics['holdout'].passed}/{report.split_metrics['holdout'].total} passed",
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Intent accuracy | {format_metric(metrics.intent_accuracy)} |",
        f"| Route accuracy | {format_metric(metrics.route_accuracy)} |",
        f"| Retrieval hit@k | {format_metric(metrics.retrieval_hit_at_k)} |",
        f"| Retrieval recall@k | {format_metric(metrics.retrieval_recall_at_k)} |",
        f"| Citation validity | {format_metric(metrics.citation_validity_rate)} |",
        f"| Expected citation match | {format_metric(metrics.expected_citation_match_rate)} |",
        f"| Grounded answer pass | {format_metric(metrics.grounded_answer_pass_rate)} |",
        f"| Refusal accuracy | {format_metric(metrics.refusal_accuracy)} |",
        f"| Fabricated answer rate | {format_metric(metrics.fabricated_answer_rate)} |",
        "",
        "## Split Metrics",
        "",
        "| Split | Cases | Passed | Pass rate |",
        "|---|---:|---:|---:|",
        f"| Core | {report.split_metrics['core'].total} | {report.split_metrics['core'].passed} | {format_metric(report.split_metrics['core'].pass_rate)} |",
        f"| Holdout | {report.split_metrics['holdout'].total} | {report.split_metrics['holdout'].passed} | {format_metric(report.split_metrics['holdout'].pass_rate)} |",
        "",
        "## Failed Cases",
        "",
    ]
    if report.failures:
        for failure in report.failures:
            lines.append(f"- `{failure.case_id}`: {', '.join(failure.failed_checks)}")
    else:
        lines.append("No failed cases.")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in report.limitations)
    return "\n".join(lines) + "\n"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def safe_filename(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", value).strip("-") or "phase6-run"


def format_metric(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.3f}"


def normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
