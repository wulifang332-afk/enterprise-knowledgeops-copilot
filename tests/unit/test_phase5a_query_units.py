from __future__ import annotations

from pathlib import Path

import pytest

from backend.app.query.answer import DeterministicAnswerComposer
from backend.app.query.classifier import RuleBasedQueryClassifier
from backend.app.query.router import QueryRouter
from backend.app.query.schema import (
    AnswerGenerationStatus,
    AnswerRefusalReason,
    EvidencePack,
    EvidencePackStatus,
    QueryIntent,
    QueryRequest,
    QueryRoute,
    RefusalReason,
)


def test_query_classifier_is_deterministic_for_phase5a_intents() -> None:
    classifier = RuleBasedQueryClassifier()
    cases = {
        "Northstar Example Group ownership": QueryIntent.FACT_LOOKUP,
        "Which approval form is required for vendor payments?": QueryIntent.POLICY_LOOKUP,
        "What is the Severity 1 incident workflow in ServiceNow?": QueryIntent.PROCESS_LOOKUP,
        "Who approves vendor payments above USD 50,000?": QueryIntent.MULTI_HOP,
        "Show graph relationships for ServiceNow": QueryIntent.GRAPH_EXPLORATION,
        "What is the weather tomorrow?": QueryIntent.OUT_OF_SCOPE,
        "Write the final answer for vendor approvals.": QueryIntent.UNSUPPORTED,
    }

    for query, expected in cases.items():
        assert classifier.classify(query) == expected
        assert classifier.classify(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "What is the capital of France?",
        "Who is the president of the United States?",
        "What is the weather in Singapore?",
        "Write a Python function to reverse a string.",
        "Tell me a joke.",
        "What is 2 + 2?",
    ],
)
def test_query_classifier_rejects_non_enterprise_questions(query: str) -> None:
    assert RuleBasedQueryClassifier().classify(query) == QueryIntent.OUT_OF_SCOPE


def test_query_router_routes_policy_lookup_with_policy_filters() -> None:
    decision = QueryRouter().route(
        request=QueryRequest(query="Which approval form is required for vendor payments?", include_graph=True),
        intent=QueryIntent.POLICY_LOOKUP,
    )

    assert decision.route == QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS
    assert decision.include_retrieval is True
    assert decision.include_graph is True
    assert decision.filters.policy_types == ["policy"]
    assert decision.refusal_reason is None


def test_query_router_routes_fact_lookup_to_hybrid_retrieval_only() -> None:
    decision = QueryRouter().route(
        request=QueryRequest(query="Northstar Example Group ownership"),
        intent=QueryIntent.FACT_LOOKUP,
    )

    assert decision.route == QueryRoute.HYBRID_RETRIEVAL
    assert decision.include_retrieval is True
    assert decision.include_graph is False
    assert decision.graph_depth == 1


def test_query_router_routes_process_lookup_to_graph_context() -> None:
    decision = QueryRouter().route(
        request=QueryRequest(query="What is the Severity 1 incident workflow in ServiceNow?"),
        intent=QueryIntent.PROCESS_LOOKUP,
    )

    assert decision.route == QueryRoute.HYBRID_RETRIEVAL_WITH_GRAPH_CONTEXT
    assert decision.include_retrieval is True
    assert decision.include_graph is True
    assert decision.graph_depth == 1


def test_query_router_routes_refusals_without_evidence_collection() -> None:
    out_of_scope = QueryRouter().route(
        request=QueryRequest(query="What is the weather tomorrow?"),
        intent=QueryIntent.OUT_OF_SCOPE,
    )
    unsupported = QueryRouter().route(
        request=QueryRequest(query="Write the final answer for vendor approvals."),
        intent=QueryIntent.UNSUPPORTED,
    )

    assert out_of_scope.route == QueryRoute.STRUCTURED_REFUSAL
    assert out_of_scope.refusal_reason == RefusalReason.OUT_OF_SCOPE
    assert out_of_scope.include_retrieval is False
    assert unsupported.refusal_reason == RefusalReason.UNSUPPORTED_IN_PHASE_5A
    assert unsupported.include_graph is False


def test_query_router_routes_multi_hop_to_depth_two_graph_context() -> None:
    decision = QueryRouter().route(
        request=QueryRequest(query="Who approves vendor payments above USD 50,000?"),
        intent=QueryIntent.MULTI_HOP,
    )

    assert decision.route == QueryRoute.HYBRID_RETRIEVAL_WITH_GRAPH_CONTEXT
    assert decision.include_retrieval is True
    assert decision.include_graph is True
    assert decision.graph_depth == 2


def test_query_request_defaults_to_no_answer_generation() -> None:
    request = QueryRequest(query="Which approval form is required for vendor payments?")

    assert request.generate_answer is False


def test_answer_composer_refuses_when_evidence_pack_has_no_citable_evidence() -> None:
    pack = EvidencePack(
        request_id="empty",
        query="Which approval form is required for vendor payments?",
        intent=QueryIntent.POLICY_LOOKUP,
        route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
        status=EvidencePackStatus.EVIDENCE_READY,
    )

    result = DeterministicAnswerComposer().compose(pack)

    assert result.answer is None
    assert result.answer_citations == []
    assert result.answer_generation_status == AnswerGenerationStatus.INSUFFICIENT_EVIDENCE
    assert result.answer_refusal_reason == AnswerRefusalReason.NO_CITABLE_EVIDENCE
    assert not hasattr(result, "final_answer")


def test_answer_composer_has_no_external_llm_dependency() -> None:
    import backend.app.query.answer as answer_module

    source_path = answer_module.__file__
    assert source_path
    source = Path(source_path).read_text(encoding="utf-8")

    assert "openai" not in source.casefold()
    assert "anthropic" not in source.casefold()
    assert "llm" not in source.casefold()
    assert "httpx" not in source.casefold()
