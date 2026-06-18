from __future__ import annotations

import shutil
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.graph.service import GraphService
from backend.app.query.schema import EvidencePackStatus, QueryIntent, QueryRequest
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
    assert "Final answer generation is planned for Phase 5B." == pack.next_phase_note
    assert not hasattr(pack, "answer")
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
        assert not hasattr(out_of_scope, "answer")
        assert not hasattr(out_of_scope, "final_answer")

    assert unsupported.status == EvidencePackStatus.REFUSED
    assert unsupported.refusal_reason == "UNSUPPORTED_IN_PHASE_5A"
    assert "Phase 5A" in " ".join(unsupported.limitations)
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
