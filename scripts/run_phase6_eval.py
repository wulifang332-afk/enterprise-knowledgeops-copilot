from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.evaluation.service import EvaluationService


def format_percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.1%}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Phase 6 KnowledgeOps evaluation.")
    parser.add_argument("--dataset", type=Path, default=None)
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit 1 when one or more evaluation cases fail. Execution errors always exit non-zero.",
    )
    args = parser.parse_args()

    settings = AppSettings(project_root=PROJECT_ROOT)
    service = EvaluationService(settings=settings, dataset_path=args.dataset)
    try:
        report = service.run(persist=True)
    except KnowledgeOpsError as exc:
        print(f"{exc.error_code.value}: {exc.message}", file=sys.stderr)
        if exc.details:
            print(exc.details, file=sys.stderr)
        return 2

    metrics = report.metrics
    print(f"Phase 6 evaluation: {report.passed_cases}/{report.total_cases} cases passed")
    print(f"Dataset: {report.dataset_version}")
    print(f"Core: {report.split_metrics['core'].passed}/{report.split_metrics['core'].total} passed")
    print(f"Holdout: {report.split_metrics['holdout'].passed}/{report.split_metrics['holdout'].total} passed")
    print(f"Intent accuracy: {format_percentage(metrics.intent_accuracy)}")
    print(f"Route accuracy: {format_percentage(metrics.route_accuracy)}")
    print(f"Retrieval hit@k: {format_percentage(metrics.retrieval_hit_at_k)}")
    print(f"Citation validity: {format_percentage(metrics.citation_validity_rate)}")
    print(f"Grounded answer pass: {format_percentage(metrics.grounded_answer_pass_rate)}")
    print(f"Refusal accuracy: {format_percentage(metrics.refusal_accuracy)}")
    print(f"Fabricated answer rate: {format_percentage(metrics.fabricated_answer_rate)}")
    print(f"JSON report: {service.latest_json_path.relative_to(PROJECT_ROOT)}")
    print(f"Markdown report: {service.latest_markdown_path.relative_to(PROJECT_ROOT)}")

    if args.fail_on_regression and report.failed_cases:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
