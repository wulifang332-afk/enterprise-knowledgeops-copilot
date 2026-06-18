from __future__ import annotations

from collections import Counter
import shutil
from pathlib import Path

import pytest

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.graph.service import GraphService
from backend.app.graph.schema import RelationType
from backend.app.retrieval.corpus import ProcessedCorpus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCUMENT_LEVEL_RELATIONS = {"OWNS", "APPLIES_TO", "HAS_ACCESS_LEVEL", "GOVERNS"}


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    return AppSettings(project_root=tmp_path, data_dir=data_dir)


def test_graph_rebuild_from_processed_documents_has_expected_nodes_and_edges(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GraphService(settings)

    result = service.rebuild()
    snapshot = service.snapshot()
    labels = {node.label for node in snapshot.nodes}
    node_by_id = {node.node_id: node for node in snapshot.nodes}

    assert result.source_chunk_count == 40
    assert result.node_count > 0
    assert result.edge_count > 0
    for label in ("Vendor Payment Request Form", "ServiceNow", "Severity 1", "15 minutes", "DPO"):
        assert label in labels

    expected_edges = {
        ("Vendor Payment Approval Policy", RelationType.REQUIRES, "Vendor Payment Request Form"),
        ("IT Incident Escalation SOP", RelationType.USES_SYSTEM, "ServiceNow"),
        ("Severity 1", RelationType.HAS_TIME_REQUIREMENT, "15 minutes"),
        ("Cross-border Data Handling Policy", RelationType.ESCALATES_TO, "DPO"),
    }
    actual_edges = {
        (
            node_by_id[edge.source_node_id].label,
            edge.relation_type,
            node_by_id[edge.target_node_id].label,
        )
        for edge in snapshot.edges
    }
    assert expected_edges.issubset(actual_edges)


def test_graph_neighborhood_depth_limit_and_contents(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GraphService(settings)
    service.rebuild()
    servicenow = next(node for node in service.nodes(label_contains="ServiceNow") if node.label == "ServiceNow")

    selected, nodes, edges = service.neighborhood(node_id=servicenow.node_id, depth=1)

    assert selected.label == "ServiceNow"
    assert any(edge.target_node_id == servicenow.node_id for edge in edges)
    assert any(node.label == "IT Incident Escalation SOP" for node in nodes)
    with pytest.raises(KnowledgeOpsError):
        service.neighborhood(node_id=servicenow.node_id, depth=3)


def test_graph_rebuild_is_deterministic_and_noise_is_bounded(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GraphService(settings)

    first = service.rebuild()
    first_artifact = Path(first.artifact_path).read_text(encoding="utf-8")
    second = service.rebuild()
    second_artifact = Path(second.artifact_path).read_text(encoding="utf-8")
    snapshot = service.snapshot()

    assert first.node_count == second.node_count
    assert first.edge_count == second.edge_count
    assert first_artifact == second_artifact
    assert second.edge_count < 300
    assert mentions_count(snapshot.edges) <= 140
    assert semantic_duplicate_surplus(snapshot.edges) <= 70

    document_level_counts = Counter(
        (edge.source_node_id, edge.relation_type.value, edge.target_node_id, edge.source_doc_id)
        for edge in snapshot.edges
        if edge.relation_type.value in DOCUMENT_LEVEL_RELATIONS
    )
    assert all(count == 1 for count in document_level_counts.values())


def test_mentions_are_fallback_only_when_stronger_relation_exists(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GraphService(settings)
    service.rebuild()
    snapshot = service.snapshot()
    strong_pairs = {
        (edge.source_node_id, edge.target_node_id, edge.source_doc_id)
        for edge in snapshot.edges
        if edge.relation_type != RelationType.MENTIONS
    }

    assert not any(
        edge.relation_type == RelationType.MENTIONS
        and (edge.source_node_id, edge.target_node_id, edge.source_doc_id) in strong_pairs
        for edge in snapshot.edges
    )


def test_graph_edge_evidence_quotes_are_grounded_in_source_chunks(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    service = GraphService(settings)
    service.rebuild()
    snapshot = service.snapshot()
    chunk_text_by_id = {
        record.chunk.chunk_id: normalize_space(record.chunk.text)
        for record in ProcessedCorpus(settings).load()
    }

    assert snapshot.edges
    assert all(normalize_space(edge.evidence_quote) in chunk_text_by_id[edge.source_chunk_id] for edge in snapshot.edges)


def mentions_count(edges) -> int:
    return sum(1 for edge in edges if edge.relation_type == RelationType.MENTIONS)


def semantic_duplicate_surplus(edges) -> int:
    counts = Counter((edge.source_node_id, edge.relation_type.value, edge.target_node_id) for edge in edges)
    return sum(count - 1 for count in counts.values() if count > 1)


def normalize_space(value: str) -> str:
    return " ".join(value.split())
