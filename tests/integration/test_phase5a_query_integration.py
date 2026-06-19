from __future__ import annotations

import shutil
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.graph.service import GraphService
from backend.app.query.schema import AnswerGenerationStatus, AnswerRefusalReason, EvidencePackStatus, QueryIntent, QueryRequest
from backend.app.query.service import QueryPlanningService
from backend.app.retrieval.indexing import IndexRebuildService

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    IndexRebuildService(settings).rebuild_all()
    GraphService(settings).rebuild()
    return settings


def test_policy_lookup_evidence_pack_has_retrieval_citations_and_graph_edges(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(query="Which approval form is required for vendor payments?", top_k=5, include_graph=True),
        request_id="test-request",
    )

    assert pack.request_id == "test-request"
    assert pack.intent == QueryIntent.POLICY_LOOKUP
    assert pack.status == EvidencePackStatus.EVIDENCE_READY
    assert pack.retrieval_evidence
    assert pack.citations
    assert all(item.citation.quote_hash for item in pack.retrieval_evidence)
    assert any(item.doc_id == "vendor-payment-approval-policy-v1-0" for item in pack.retrieval_evidence)
    assert any(edge.evidence_quote for edge in pack.graph_evidence.edges)
    assert any(edge.relation_type.value == "REQUIRES" for edge in pack.graph_evidence.edges)
    assert "Phase 5B can generate citation-grounded answers" in pack.next_phase_note
    assert pack.answer is None
    assert pack.answer_citations == []
    assert pack.answer_generation_status == AnswerGenerationStatus.NOT_REQUESTED
    assert not hasattr(pack, "final_answer")


def test_graph_exploration_route_returns_graph_evidence_without_retrieval(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(query="Show graph relationships for ServiceNow", include_graph=True),
        request_id="graph-request",
    )

    assert pack.intent == QueryIntent.GRAPH_EXPLORATION
    assert pack.retrieval_evidence == []
    assert any(node.label == "ServiceNow" for node in pack.graph_evidence.matched_nodes)
    assert pack.graph_evidence.edges
    assert any(edge.evidence_quote for edge in pack.graph_evidence.edges)


def test_process_system_query_prioritizes_servicenow_uses_system_edge(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(query="What system is used for Severity 1 incidents?", include_graph=True),
        request_id="system-query",
    )
    nodes = {node.node_id: node for node in [*pack.graph_evidence.matched_nodes, *pack.graph_evidence.neighboring_nodes]}

    assert pack.intent == QueryIntent.PROCESS_LOOKUP
    assert any(node.label == "ServiceNow" for node in nodes.values())
    assert any(
        edge.relation_type.value == "USES_SYSTEM"
        and nodes.get(edge.target_node_id)
        and nodes[edge.target_node_id].label == "ServiceNow"
        for edge in pack.graph_evidence.edges
    )
    assert pack.graph_evidence.edges[0].relation_type.value in {"USES_SYSTEM", "HAS_TIME_REQUIREMENT"}


def test_out_of_scope_and_unsupported_queries_return_structured_refusals(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    out_of_scope_queries = [
        "What is the capital of France?",
        "Who is the president of the United States?",
        "What is the weather in Singapore?",
        "Write a Python function to reverse a string.",
        "Tell me a joke.",
        "What is 2 + 2?",
    ]
    unsupported = service.plan(
        request=QueryRequest(query="Write the final answer for vendor approvals."),
        request_id="unsupported",
    )

    for query in out_of_scope_queries:
        out_of_scope = service.plan(request=QueryRequest(query=query), request_id="out")
        assert out_of_scope.intent == QueryIntent.OUT_OF_SCOPE
        assert out_of_scope.status == EvidencePackStatus.REFUSED
        assert out_of_scope.refusal_reason == "OUT_OF_SCOPE"
        assert out_of_scope.retrieval_evidence == []
        assert out_of_scope.graph_evidence.edges == []
        assert out_of_scope.answer is None
        assert out_of_scope.answer_generation_status == AnswerGenerationStatus.NOT_REQUESTED
        assert not hasattr(out_of_scope, "final_answer")

    assert unsupported.status == EvidencePackStatus.REFUSED
    assert unsupported.refusal_reason == "UNSUPPORTED_IN_PHASE_5A"
    assert "free-form answer drafting" in " ".join(unsupported.limitations)
    assert unsupported.retrieval_evidence == []
    assert unsupported.graph_evidence.edges == []


def test_multi_hop_route_combines_retrieval_and_depth_two_graph_evidence(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(query="Who approves vendor payments above USD 50,000?", include_graph=True),
        request_id="multi-hop",
    )

    assert pack.intent == QueryIntent.MULTI_HOP
    assert pack.retrieval_evidence
    assert pack.graph_evidence.neighboring_nodes
    assert pack.graph_evidence.edges
    assert any(item.citation.start_char < item.citation.end_char for item in pack.retrieval_evidence)


def test_cross_border_multi_hop_graph_evidence_prefers_retrieved_policy_context(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(query="How does cross-border data approval work between APAC and EU?", include_graph=True),
        request_id="cross-border",
    )

    assert pack.intent == QueryIntent.MULTI_HOP
    assert pack.retrieval_evidence
    assert pack.graph_evidence.edges
    assert any(edge.source_doc_id == "cross-border-data-policy-v1-0" for edge in pack.graph_evidence.edges[:10])
    assert any(edge.relation_type.value in {"APPLIES_TO", "ESCALATES_TO"} for edge in pack.graph_evidence.edges)
    assert not any(
        edge.source_doc_id == "it-incident-escalation-sop-v1-0" and edge.relation_type.value == "ESCALATES_TO"
        for edge in pack.graph_evidence.edges[:20]
    )


def test_generate_answer_false_preserves_evidence_pack_behavior(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(
            query="Which approval form is required for vendor payments?",
            top_k=5,
            include_graph=True,
            generate_answer=False,
        ),
        request_id="no-answer",
    )

    assert pack.status == EvidencePackStatus.EVIDENCE_READY
    assert pack.retrieval_evidence
    assert pack.graph_evidence.edges
    assert pack.answer is None
    assert pack.answer_citations == []
    assert pack.answer_generation_status == AnswerGenerationStatus.NOT_REQUESTED
    assert pack.answer_refusal_reason is None
    assert not hasattr(pack, "final_answer")


def test_vendor_payment_query_generates_citation_grounded_answer(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(
            query="Which approval form is required for vendor payments?",
            top_k=5,
            include_graph=True,
            generate_answer=True,
        ),
        request_id="vendor-answer",
    )

    citation_ids = {citation.citation_id for citation in pack.citations}
    answer_citation_ids = {citation.citation_id for citation in pack.answer_citations}

    assert pack.answer_generation_status == AnswerGenerationStatus.GENERATED
    assert pack.answer
    assert "Vendor Payment Request Form" in pack.answer
    assert pack.answer_citations
    assert answer_citation_ids.issubset(citation_ids)
    assert all(f"[{citation.citation_id}]" in pack.answer for citation in pack.answer_citations)
    assert not hasattr(pack, "final_answer")


def test_severity_one_query_generates_servicenow_answer(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(
            query="What system is used for Severity 1 incidents?",
            top_k=5,
            include_graph=True,
            generate_answer=True,
        ),
        request_id="system-answer",
    )

    citation_ids = {citation.citation_id for citation in pack.citations}
    answer_citation_ids = {citation.citation_id for citation in pack.answer_citations}

    assert pack.answer_generation_status == AnswerGenerationStatus.GENERATED
    assert pack.answer
    assert "ServiceNow" in pack.answer
    assert "USES_SYSTEM" in {edge.relation_type.value for edge in pack.graph_evidence.edges}
    assert pack.answer_citations
    assert answer_citation_ids.issubset(citation_ids)
    assert all(sentence.strip().endswith("]") for sentence in pack.answer.split(".") if sentence.strip())


def test_cross_border_query_generates_cautious_cited_answer(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(
            query="How does cross-border data approval work between APAC and EU?",
            top_k=5,
            include_graph=True,
            generate_answer=True,
        ),
        request_id="cross-border-answer",
    )

    assert pack.answer_generation_status == AnswerGenerationStatus.GENERATED
    assert pack.answer
    assert "APAC" in pack.answer
    assert "EU" in pack.answer
    assert "Data Protection Officer" in pack.answer
    assert pack.answer_citations
    assert all(citation.doc_id == "cross-border-data-policy-v1-0" for citation in pack.answer_citations)
    assert not any(
        edge.source_doc_id == "it-incident-escalation-sop-v1-0" and edge.relation_type.value == "ESCALATES_TO"
        for edge in pack.graph_evidence.edges[:20]
    )


def test_generate_answer_refuses_out_of_scope_and_unsupported_queries(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    out_of_scope = service.plan(
        request=QueryRequest(query="What is the capital of France?", generate_answer=True),
        request_id="capital",
    )
    unsupported = service.plan(
        request=QueryRequest(query="Write the final answer for vendor approvals.", generate_answer=True),
        request_id="unsupported",
    )

    assert out_of_scope.intent == QueryIntent.OUT_OF_SCOPE
    assert out_of_scope.status == EvidencePackStatus.REFUSED
    assert out_of_scope.answer is None
    assert out_of_scope.answer_generation_status == AnswerGenerationStatus.REFUSED
    assert out_of_scope.answer_refusal_reason == AnswerRefusalReason.OUT_OF_SCOPE
    assert out_of_scope.retrieval_evidence == []
    assert out_of_scope.graph_evidence.edges == []

    assert unsupported.status == EvidencePackStatus.REFUSED
    assert unsupported.answer is None
    assert unsupported.answer_generation_status == AnswerGenerationStatus.REFUSED
    assert unsupported.answer_refusal_reason == AnswerRefusalReason.UNSUPPORTED_IN_PHASE_5A


def test_generate_answer_refuses_insufficient_evidence_without_fabrication(tmp_path: Path) -> None:
    service = QueryPlanningService(make_settings(tmp_path))

    pack = service.plan(
        request=QueryRequest(
            query="Tell me the company's travel reimbursement policy for Mars employees.",
            top_k=5,
            include_graph=True,
            generate_answer=True,
        ),
        request_id="mars",
    )

    assert pack.intent == QueryIntent.POLICY_LOOKUP
    assert pack.answer is None
    assert pack.answer_citations == []
    assert pack.answer_generation_status == AnswerGenerationStatus.INSUFFICIENT_EVIDENCE
    assert pack.answer_refusal_reason == AnswerRefusalReason.INSUFFICIENT_EVIDENCE
    assert "mars" in (pack.grounding_summary or "").casefold()
