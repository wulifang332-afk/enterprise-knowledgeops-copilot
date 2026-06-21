from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import ValidationError

from backend.app.api.dependencies import get_settings
from backend.app.api.utils import ProcessedRegistryReader
from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.evaluation.schema import EvaluationReport
from backend.app.graph.schema import GraphArtifact
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.studio import EvaluationSummaryResponse, WorkspaceSummaryResponse

router = APIRouter(prefix="/api/v1", tags=["studio"])


@router.get("/workspace/summary", response_model=WorkspaceSummaryResponse)
def workspace_summary(settings: AppSettings = Depends(get_settings)) -> WorkspaceSummaryResponse:
    registry = ProcessedRegistryReader(settings)
    documents = registry.documents()
    chunks = registry.chunks()
    graph_nodes, graph_edges = _graph_counts(settings)
    return WorkspaceSummaryResponse(
        documents=len(documents),
        chunks=len(chunks),
        graph_nodes=graph_nodes,
        graph_edges=graph_edges,
    )


@router.get("/evaluation/summary", response_model=EvaluationSummaryResponse)
def evaluation_summary(settings: AppSettings = Depends(get_settings)) -> EvaluationSummaryResponse:
    report_path = settings.evaluation_dir / "latest_report.json"
    if not report_path.exists():
        return EvaluationSummaryResponse(available=False)

    try:
        report = EvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise KnowledgeOpsError(
            ErrorCode.INVALID_EVALUATION_CASE,
            "The latest Phase 6 evaluation report is invalid.",
            {"reason": str(exc)},
        ) from exc

    core = report.split_metrics.get("core")
    holdout = report.split_metrics.get("holdout")
    return EvaluationSummaryResponse(
        available=True,
        run_id=report.run_id,
        timestamp=report.timestamp,
        dataset_version=report.dataset_version,
        total_cases=report.total_cases,
        passed_cases=report.passed_cases,
        failed_cases=report.failed_cases,
        pass_rate=report.metrics.pass_rate,
        intent_accuracy=report.metrics.intent_accuracy,
        route_accuracy=report.metrics.route_accuracy,
        citation_validity_rate=report.metrics.citation_validity_rate,
        grounded_answer_pass_rate=report.metrics.grounded_answer_pass_rate,
        refusal_accuracy=report.metrics.refusal_accuracy,
        fabricated_answer_rate=report.metrics.fabricated_answer_rate,
        core_total=core.total if core else 0,
        core_passed=core.passed if core else 0,
        holdout_total=holdout.total if holdout else 0,
        holdout_passed=holdout.passed if holdout else 0,
    )


def _graph_counts(settings: AppSettings) -> tuple[int, int]:
    artifact_path = settings.graph_dir / "knowledge_graph.json"
    if not artifact_path.exists():
        return 0, 0

    try:
        artifact = GraphArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError) as exc:
        raise KnowledgeOpsError(
            ErrorCode.GRAPH_UNAVAILABLE,
            "Graph artifact is invalid.",
            {"reason": str(exc)},
        ) from exc
    return len(artifact.nodes), len(artifact.edges)
