from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field, model_validator

from backend.app.graph.schema import RelationType
from backend.app.query.schema import (
    AnswerGenerationStatus,
    AnswerRefusalReason,
    EvidencePackStatus,
    QueryIntent,
    QueryRoute,
    RefusalReason,
)
from backend.app.schemas.documents import StrictBaseModel


class EvaluationSplit(StrEnum):
    CORE = "core"
    HOLDOUT = "holdout"


class EvaluationCase(StrictBaseModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{2,99}$")
    split: EvaluationSplit = EvaluationSplit.CORE
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    generate_answer: bool = False
    include_graph: bool = True
    expected_intent: QueryIntent
    expected_route: QueryRoute
    expected_status: EvidencePackStatus
    expected_answer_generation_status: AnswerGenerationStatus
    expected_refusal_reason: RefusalReason | None = None
    expected_answer_refusal_reason: AnswerRefusalReason | None = None
    expected_retrieval_doc_ids: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_citation_doc_ids: list[str] = Field(default_factory=list)
    expected_graph_relations: list[RelationType] = Field(default_factory=list)
    expected_answer_contains: list[str] = Field(default_factory=list)
    forbidden_answer_contains: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_expectations(self) -> "EvaluationCase":
        if self.expected_status == EvidencePackStatus.REFUSED and self.expected_answer_contains:
            raise ValueError("refusal cases cannot require answer phrases")
        if self.expected_answer_generation_status != AnswerGenerationStatus.GENERATED and self.expected_answer_contains:
            raise ValueError("non-generated cases cannot require answer phrases")
        if self.expected_answer_generation_status == AnswerGenerationStatus.GENERATED:
            if not self.generate_answer:
                raise ValueError("generated-answer expectations require generate_answer=true")
            if not self.expected_answer_contains:
                raise ValueError("generated-answer cases require expected_answer_contains")
            if not self.expected_citation_doc_ids:
                raise ValueError("generated-answer cases require expected_citation_doc_ids")
        return self


class EvaluationDataset(StrictBaseModel):
    dataset_version: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=500)
    cases: list[EvaluationCase] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_case_ids(self) -> "EvaluationDataset":
        case_ids = [case.case_id for case in self.cases]
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("evaluation case IDs must be unique")
        return self


class ExpectedOutcome(StrictBaseModel):
    intent: QueryIntent
    route: QueryRoute
    status: EvidencePackStatus
    answer_generation_status: AnswerGenerationStatus
    refusal_reason: RefusalReason | None = None
    answer_refusal_reason: AnswerRefusalReason | None = None
    retrieval_doc_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    citation_doc_ids: list[str] = Field(default_factory=list)
    graph_relations: list[RelationType] = Field(default_factory=list)
    answer_contains: list[str] = Field(default_factory=list)


class ActualOutcome(StrictBaseModel):
    intent: QueryIntent
    route: QueryRoute
    status: EvidencePackStatus
    answer_generation_status: AnswerGenerationStatus
    refusal_reason: RefusalReason | None = None
    answer_refusal_reason: AnswerRefusalReason | None = None
    retrieval_doc_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    evidence_citation_ids: list[str] = Field(default_factory=list)
    answer_citation_ids: list[str] = Field(default_factory=list)
    answer_citation_doc_ids: list[str] = Field(default_factory=list)
    graph_relations: list[RelationType] = Field(default_factory=list)
    answer: str | None = None
    grounding_summary: str | None = None


class EvaluationCaseResult(StrictBaseModel):
    case_id: str
    split: EvaluationSplit
    query: str
    expected: ExpectedOutcome
    actual: ActualOutcome
    passed: bool
    failed_checks: list[str] = Field(default_factory=list)
    retrieval_hit_at_k: bool | None = None
    retrieval_recall_at_k: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_subset_valid: bool | None = None
    expected_citation_match: bool | None = None
    grounding_pass: bool | None = None
    refusal_correct: bool | None = None
    fabricated_answer: bool = False


class EvaluationMetrics(StrictBaseModel):
    pass_rate: float = Field(ge=0.0, le=1.0)
    intent_accuracy: float = Field(ge=0.0, le=1.0)
    route_accuracy: float = Field(ge=0.0, le=1.0)
    retrieval_hit_at_k: float | None = Field(default=None, ge=0.0, le=1.0)
    retrieval_recall_at_k: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_chunk_presence_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    answer_citation_non_empty_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    citation_validity_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_citation_match_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    grounded_answer_pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    refusal_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    out_of_scope_refusal_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    unsupported_refusal_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    insufficient_evidence_refusal_accuracy: float | None = Field(default=None, ge=0.0, le=1.0)
    fabricated_answer_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class PerIntentMetrics(StrictBaseModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    pass_rate: float = Field(ge=0.0, le=1.0)
    intent_accuracy: float = Field(ge=0.0, le=1.0)


class SplitMetrics(StrictBaseModel):
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    pass_rate: float | None = Field(default=None, ge=0.0, le=1.0)


class EvaluationReport(StrictBaseModel):
    run_id: str
    timestamp: datetime
    dataset_version: str
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    metrics: EvaluationMetrics
    split_metrics: dict[str, SplitMetrics]
    per_intent_metrics: dict[str, PerIntentMetrics]
    intent_confusion_summary: dict[str, dict[str, int]]
    per_case_results: list[EvaluationCaseResult]
    failures: list[EvaluationCaseResult]
    limitations: list[str]


class EvaluationReportResponse(StrictBaseModel):
    request_id: str
    report: EvaluationReport


class EvaluationCasesResponse(StrictBaseModel):
    request_id: str
    dataset_version: str
    total_cases: int = Field(ge=0)
    items: list[EvaluationCase]
