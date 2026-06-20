from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from backend.app.evaluation.metrics import aggregate_metrics, evaluate_case
from backend.app.evaluation.schema import (
    EvaluationCase,
    EvaluationDataset,
    EvaluationMetrics,
    EvaluationReport,
    EvaluationSplit,
    PerIntentMetrics,
    SplitMetrics,
)
from backend.app.evaluation.service import EvaluationService, render_markdown_report
from backend.app.graph.schema import RelationType
from backend.app.query.schema import (
    AnswerGenerationStatus,
    AnswerRefusalReason,
    EvidencePackStatus,
    QueryIntent,
    QueryRoute,
    RefusalReason,
)
from dashboard.evaluation_formatting import format_percentage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = PROJECT_ROOT / "evaluation" / "datasets" / "phase6_eval_cases.json"


def test_phase6_dataset_validates_with_unique_supported_cases() -> None:
    dataset = EvaluationService.__new__(EvaluationService)
    dataset.dataset_path = DATASET_PATH
    loaded = EvaluationService.load_dataset(dataset)

    assert loaded.dataset_version == "phase6-v1"
    assert len(loaded.cases) == 22
    assert len({case.case_id for case in loaded.cases}) == len(loaded.cases)
    assert set(case.expected_intent for case in loaded.cases) == set(QueryIntent)
    assert sum(case.split == EvaluationSplit.CORE for case in loaded.cases) == 17
    assert sum(case.split == EvaluationSplit.HOLDOUT for case in loaded.cases) == 5


def test_phase6_dataset_rejects_duplicate_case_ids() -> None:
    case = basic_case()

    with pytest.raises(ValidationError, match="unique"):
        EvaluationDataset(dataset_version="test", description="duplicate fixture", cases=[case, case])


def test_refusal_case_rejects_expected_answer_phrases() -> None:
    with pytest.raises(ValidationError, match="cannot require answer phrases"):
        EvaluationCase(
            case_id="bad_refusal",
            query="What is the capital of France?",
            generate_answer=True,
            expected_intent=QueryIntent.OUT_OF_SCOPE,
            expected_route=QueryRoute.STRUCTURED_REFUSAL,
            expected_status=EvidencePackStatus.REFUSED,
            expected_answer_generation_status=AnswerGenerationStatus.REFUSED,
            expected_refusal_reason=RefusalReason.OUT_OF_SCOPE,
            expected_answer_refusal_reason=AnswerRefusalReason.OUT_OF_SCOPE,
            expected_answer_contains=["Paris"],
        )


def test_evaluate_case_calculates_retrieval_and_citation_checks() -> None:
    case = basic_case()
    pack = SimpleNamespace(
        intent=QueryIntent.POLICY_LOOKUP,
        route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
        status=EvidencePackStatus.EVIDENCE_READY,
        refusal_reason=None,
        answer_generation_status=AnswerGenerationStatus.GENERATED,
        answer_refusal_reason=None,
        retrieval_evidence=[SimpleNamespace(doc_id="doc-1", chunk_id="chunk-1")],
        citations=[SimpleNamespace(citation_id="CIT-1")],
        answer_citations=[SimpleNamespace(citation_id="CIT-1", doc_id="doc-1")],
        graph_evidence=SimpleNamespace(
            edges=[SimpleNamespace(relation_type=RelationType.REQUIRES)]
        ),
        answer="The required form is Form A [CIT-1].",
        grounding_summary="Grounded in CIT-1.",
    )

    result = evaluate_case(case, pack)

    assert result.passed is True
    assert result.retrieval_hit_at_k is True
    assert result.retrieval_recall_at_k == 1.0
    assert result.citation_subset_valid is True
    assert result.expected_citation_match is True
    assert result.grounding_pass is True


def test_evaluate_case_detects_refusal_and_fabricated_answer() -> None:
    case = EvaluationCase(
        case_id="out_scope",
        query="What is the capital of France?",
        generate_answer=True,
        expected_intent=QueryIntent.OUT_OF_SCOPE,
        expected_route=QueryRoute.STRUCTURED_REFUSAL,
        expected_status=EvidencePackStatus.REFUSED,
        expected_answer_generation_status=AnswerGenerationStatus.REFUSED,
        expected_refusal_reason=RefusalReason.OUT_OF_SCOPE,
        expected_answer_refusal_reason=AnswerRefusalReason.OUT_OF_SCOPE,
    )
    pack = SimpleNamespace(
        intent=QueryIntent.OUT_OF_SCOPE,
        route=QueryRoute.STRUCTURED_REFUSAL,
        status=EvidencePackStatus.REFUSED,
        refusal_reason=RefusalReason.OUT_OF_SCOPE,
        answer_generation_status=AnswerGenerationStatus.REFUSED,
        answer_refusal_reason=AnswerRefusalReason.OUT_OF_SCOPE,
        retrieval_evidence=[],
        citations=[],
        answer_citations=[],
        graph_evidence=SimpleNamespace(edges=[]),
        answer="Paris",
        grounding_summary=None,
    )

    result = evaluate_case(case, pack)

    assert result.passed is False
    assert result.fabricated_answer is True
    assert result.refusal_correct is False
    assert "unexpected_answer_generated" in result.failed_checks


def test_aggregate_metrics_and_per_intent_summary() -> None:
    case = basic_case()
    pack = SimpleNamespace(
        intent=QueryIntent.POLICY_LOOKUP,
        route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
        status=EvidencePackStatus.EVIDENCE_READY,
        refusal_reason=None,
        answer_generation_status=AnswerGenerationStatus.GENERATED,
        answer_refusal_reason=None,
        retrieval_evidence=[SimpleNamespace(doc_id="doc-1", chunk_id="chunk-1")],
        citations=[SimpleNamespace(citation_id="CIT-1")],
        answer_citations=[SimpleNamespace(citation_id="CIT-1", doc_id="doc-1")],
        graph_evidence=SimpleNamespace(edges=[SimpleNamespace(relation_type=RelationType.REQUIRES)]),
        answer="The required form is Form A [CIT-1].",
        grounding_summary="Grounded in CIT-1.",
    )
    result = evaluate_case(case, pack)

    metrics, per_intent, confusion = aggregate_metrics([case], [result])

    assert metrics.retrieval_hit_at_k == 1.0
    assert metrics.citation_validity_rate == 1.0
    assert metrics.grounded_answer_pass_rate == 1.0
    assert metrics.fabricated_answer_rate is None
    assert per_intent["policy_lookup"].passed == 1
    assert confusion == {"policy_lookup": {"policy_lookup": 1}}


def test_no_generated_answer_cases_return_unavailable_answer_metrics() -> None:
    case, result = not_requested_case(with_retrieval=True)

    metrics, _, _ = aggregate_metrics([case], [result])

    assert metrics.answer_citation_non_empty_rate is None
    assert metrics.citation_validity_rate is None
    assert metrics.expected_citation_match_rate is None
    assert metrics.grounded_answer_pass_rate is None


def test_no_retrieval_expectation_cases_return_unavailable_retrieval_metrics() -> None:
    case, result = not_requested_case(with_retrieval=False)

    metrics, _, _ = aggregate_metrics([case], [result])

    assert metrics.retrieval_hit_at_k is None
    assert metrics.retrieval_recall_at_k is None
    assert metrics.expected_chunk_presence_rate is None


def test_no_refusal_cases_return_unavailable_refusal_metrics() -> None:
    case = basic_case()
    result = evaluate_case(case, generated_pack())

    metrics, _, _ = aggregate_metrics([case], [result])

    assert metrics.refusal_accuracy is None
    assert metrics.out_of_scope_refusal_accuracy is None
    assert metrics.unsupported_refusal_accuracy is None
    assert metrics.insufficient_evidence_refusal_accuracy is None
    assert metrics.fabricated_answer_rate is None


def test_markdown_and_dashboard_render_unavailable_metrics_as_na() -> None:
    report = EvaluationReport(
        run_id="na-test",
        timestamp=datetime(2026, 6, 20, tzinfo=timezone.utc),
        dataset_version="test",
        total_cases=1,
        passed_cases=1,
        failed_cases=0,
        metrics=EvaluationMetrics(pass_rate=1.0, intent_accuracy=1.0, route_accuracy=1.0),
        split_metrics={
            "core": SplitMetrics(total=1, passed=1, failed=0, pass_rate=1.0),
            "holdout": SplitMetrics(total=0, passed=0, failed=0, pass_rate=None),
        },
        per_intent_metrics={
            "fact_lookup": PerIntentMetrics(total=1, passed=1, pass_rate=1.0, intent_accuracy=1.0)
        },
        intent_confusion_summary={"fact_lookup": {"fact_lookup": 1}},
        per_case_results=[],
        failures=[],
        limitations=["test"],
    )

    markdown = render_markdown_report(report)

    assert "| Retrieval hit@k | N/A |" in markdown
    assert "| Holdout | 0 | 0 | N/A |" in markdown
    assert format_percentage(None) == "N/A"
    assert format_percentage(1.0) == "100.0%"


def basic_case() -> EvaluationCase:
    return EvaluationCase(
        case_id="policy_form",
        query="Which form is required for vendor payments?",
        generate_answer=True,
        expected_intent=QueryIntent.POLICY_LOOKUP,
        expected_route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
        expected_status=EvidencePackStatus.EVIDENCE_READY,
        expected_answer_generation_status=AnswerGenerationStatus.GENERATED,
        expected_retrieval_doc_ids=["doc-1"],
        expected_chunk_ids=["chunk-1"],
        expected_citation_doc_ids=["doc-1"],
        expected_graph_relations=[RelationType.REQUIRES],
        expected_answer_contains=["Form A"],
    )


def generated_pack() -> SimpleNamespace:
    return SimpleNamespace(
        intent=QueryIntent.POLICY_LOOKUP,
        route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
        status=EvidencePackStatus.EVIDENCE_READY,
        refusal_reason=None,
        answer_generation_status=AnswerGenerationStatus.GENERATED,
        answer_refusal_reason=None,
        retrieval_evidence=[SimpleNamespace(doc_id="doc-1", chunk_id="chunk-1")],
        citations=[SimpleNamespace(citation_id="CIT-1")],
        answer_citations=[SimpleNamespace(citation_id="CIT-1", doc_id="doc-1")],
        graph_evidence=SimpleNamespace(edges=[SimpleNamespace(relation_type=RelationType.REQUIRES)]),
        answer="The required form is Form A [CIT-1].",
        grounding_summary="Grounded in CIT-1.",
    )


def not_requested_case(*, with_retrieval: bool) -> tuple[EvaluationCase, object]:
    expected_docs = ["doc-1"] if with_retrieval else []
    case = EvaluationCase(
        case_id="not_requested_retrieval" if with_retrieval else "not_requested_graph",
        query="IT ownership evidence",
        generate_answer=False,
        expected_intent=QueryIntent.FACT_LOOKUP,
        expected_route=QueryRoute.HYBRID_RETRIEVAL,
        expected_status=EvidencePackStatus.EVIDENCE_READY,
        expected_answer_generation_status=AnswerGenerationStatus.NOT_REQUESTED,
        expected_retrieval_doc_ids=expected_docs,
    )
    pack = SimpleNamespace(
        intent=case.expected_intent,
        route=case.expected_route,
        status=case.expected_status,
        refusal_reason=None,
        answer_generation_status=AnswerGenerationStatus.NOT_REQUESTED,
        answer_refusal_reason=None,
        retrieval_evidence=(
            [SimpleNamespace(doc_id="doc-1", chunk_id="chunk-1")] if with_retrieval else []
        ),
        citations=[],
        answer_citations=[],
        graph_evidence=SimpleNamespace(edges=[]),
        answer=None,
        grounding_summary=None,
    )
    return case, evaluate_case(case, pack)
