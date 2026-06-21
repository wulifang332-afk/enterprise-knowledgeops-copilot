from __future__ import annotations

import json
from collections import Counter

from fastapi import APIRouter, Depends, Request
from pydantic import ValidationError

from backend.app.api.dependencies import get_settings
from backend.app.api.utils import ProcessedRegistryReader, request_id_from
from backend.app.core.settings import AppSettings
from backend.app.evaluation.schema import EvaluationReport
from backend.app.feedback.schema import FeedbackRecord
from backend.app.graph.schema import GraphArtifact
from backend.app.readiness.access_policy import ACCESS_LEVEL_ORDER, AccessPolicyEngine
from backend.app.schemas.readiness import (
    AccessPolicyRequest,
    AccessPolicyResponse,
    CorpusMetadataDistributions,
    PersonaListResponse,
    ReadinessEvaluationStatus,
    ReadinessGovernanceStatus,
    ReadinessGraphStatus,
    ReadinessSummaryResponse,
)

router = APIRouter(prefix="/api/v1/readiness", tags=["readiness"])
_engine = AccessPolicyEngine()
NON_GOALS = [
    "no real auth",
    "no SSO",
    "no production RBAC",
    "no production infra",
]


@router.get("/personas", response_model=PersonaListResponse)
def personas(request: Request) -> PersonaListResponse:
    return PersonaListResponse(request_id=request_id_from(request), items=_engine.personas())


@router.get("/summary", response_model=ReadinessSummaryResponse)
def summary(request: Request, settings: AppSettings = Depends(get_settings)) -> ReadinessSummaryResponse:
    return ReadinessSummaryResponse(
        request_id=request_id_from(request),
        simulation_only=True,
        personas_count=len(_engine.personas()),
        access_levels=list(ACCESS_LEVEL_ORDER),
        corpus_metadata_distributions=_corpus_metadata_distributions(settings),
        graph_status=_graph_status(settings),
        evaluation_status=_evaluation_status(settings),
        governance_status=_governance_status(settings),
        non_goals=NON_GOALS,
    )


@router.post("/access-policy", response_model=AccessPolicyResponse)
def access_policy(payload: AccessPolicyRequest, request: Request) -> AccessPolicyResponse:
    return _engine.simulate(payload, request_id=request_id_from(request))


def _corpus_metadata_distributions(settings: AppSettings) -> CorpusMetadataDistributions:
    try:
        documents = ProcessedRegistryReader(settings).documents()
    except (OSError, ValidationError, ValueError):
        return CorpusMetadataDistributions()

    departments: Counter[str] = Counter()
    regions: Counter[str] = Counter()
    policy_types: Counter[str] = Counter()
    owners: Counter[str] = Counter()
    access_levels: Counter[str] = Counter()
    for document in documents:
        metadata = document.metadata
        departments[metadata.department] += 1
        regions.update(metadata.regions)
        policy_types[metadata.policy_type.value] += 1
        owners[metadata.owner] += 1
        access_levels[metadata.access_level.value] += 1
    return CorpusMetadataDistributions(
        departments=dict(sorted(departments.items())),
        regions=dict(sorted(regions.items())),
        policy_types=dict(sorted(policy_types.items())),
        owners=dict(sorted(owners.items())),
        access_levels=dict(sorted(access_levels.items())),
    )


def _graph_status(settings: AppSettings) -> ReadinessGraphStatus:
    artifact_path = settings.graph_dir / "knowledge_graph.json"
    if not artifact_path.exists():
        return ReadinessGraphStatus()
    try:
        artifact = GraphArtifact.model_validate_json(artifact_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError):
        return ReadinessGraphStatus()
    return ReadinessGraphStatus(available=True, node_count=len(artifact.nodes), edge_count=len(artifact.edges))


def _evaluation_status(settings: AppSettings) -> ReadinessEvaluationStatus:
    report_path = settings.evaluation_dir / "latest_report.json"
    if not report_path.exists():
        return ReadinessEvaluationStatus()
    try:
        report = EvaluationReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, ValueError):
        return ReadinessEvaluationStatus()
    return ReadinessEvaluationStatus(
        available=True,
        total_cases=report.total_cases,
        passed_cases=report.passed_cases,
        pass_rate=report.metrics.pass_rate,
    )


def _governance_status(settings: AppSettings) -> ReadinessGovernanceStatus:
    feedback_path = settings.feedback_dir / "feedback.jsonl"
    if not feedback_path.exists():
        return ReadinessGovernanceStatus()

    records: list[FeedbackRecord] = []
    try:
        for line in feedback_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            records.append(FeedbackRecord.model_validate(json.loads(stripped)))
    except (OSError, json.JSONDecodeError, ValidationError, ValueError):
        return ReadinessGovernanceStatus()

    status_counts = Counter(record.review_status.value for record in records)
    return ReadinessGovernanceStatus(
        available=True,
        feedback_count=len(records),
        review_status_breakdown=dict(sorted(status_counts.items())),
    )
