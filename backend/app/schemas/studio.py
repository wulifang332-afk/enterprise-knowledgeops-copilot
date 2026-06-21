from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.app.schemas.documents import StrictBaseModel


class WorkspaceSummaryResponse(StrictBaseModel):
    documents: int = Field(ge=0)
    chunks: int = Field(ge=0)
    graph_nodes: int = Field(ge=0)
    graph_edges: int = Field(ge=0)


class EvaluationSummaryResponse(StrictBaseModel):
    available: bool
    run_id: str | None = None
    timestamp: datetime | None = None
    dataset_version: str | None = None
    total_cases: int = Field(default=0, ge=0)
    passed_cases: int = Field(default=0, ge=0)
    failed_cases: int = Field(default=0, ge=0)
    pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    intent_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    route_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_validity_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    grounded_answer_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    refusal_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    fabricated_answer_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    core_total: int = Field(default=0, ge=0)
    core_passed: int = Field(default=0, ge=0)
    holdout_total: int = Field(default=0, ge=0)
    holdout_passed: int = Field(default=0, ge=0)
