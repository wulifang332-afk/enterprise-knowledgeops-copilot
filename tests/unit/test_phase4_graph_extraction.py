from __future__ import annotations

import shutil
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.graph.extractor import RuleBasedGraphExtractor, edge_id_for, node_id_for
from backend.app.graph.schema import GraphEdge, GraphNode, NodeType, RelationType
from backend.app.graph.store import NetworkXGraphStore
from backend.app.retrieval.corpus import ProcessedCorpus

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    return AppSettings(project_root=tmp_path, data_dir=data_dir)


def chunk_by_section(settings: AppSettings, doc_id: str, section_title: str):
    for record in ProcessedCorpus(settings).load():
        if record.chunk.doc_id == doc_id and record.chunk.metadata.section_title == section_title:
            return record
    raise AssertionError(f"Missing chunk {doc_id} / {section_title}")


def test_graph_entity_extraction_is_deterministic(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    record = chunk_by_section(settings, "vendor-payment-approval-policy-v1-0", "Required Documents")
    extractor = RuleBasedGraphExtractor()

    first = extractor.extract_chunk(record)
    second = extractor.extract_chunk(record)

    assert [node.model_dump() for node in first.nodes] == [node.model_dump() for node in second.nodes]
    assert [edge.model_dump() for edge in first.edges] == [edge.model_dump() for edge in second.edges]
    assert any(node.label == "Vendor Payment Request Form" and node.type == NodeType.FORM for node in first.nodes)
    assert any(node.label == "Vendor Payment Approval Policy" and node.type == NodeType.POLICY for node in first.nodes)


def test_graph_relation_extraction_finds_expected_policy_requires_form_edge(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    record = chunk_by_section(settings, "vendor-payment-approval-policy-v1-0", "Required Documents")
    result = RuleBasedGraphExtractor().extract_chunk(record)
    node_by_id = {node.node_id: node for node in result.nodes}

    assert any(
        node_by_id[edge.source_node_id].label == "Vendor Payment Approval Policy"
        and edge.relation_type == RelationType.REQUIRES
        and node_by_id[edge.target_node_id].label == "Vendor Payment Request Form"
        and "Vendor Payment Request Form" in edge.evidence_quote
        for edge in result.edges
    )
    assert not any(
        node_by_id[edge.source_node_id].label == "Vendor Payment Approval Policy"
        and edge.relation_type == RelationType.MENTIONS
        and node_by_id[edge.target_node_id].label == "Vendor Payment Request Form"
        and edge.source_chunk_id == record.chunk.chunk_id
        for edge in result.edges
    )


def test_graph_node_and_edge_ids_are_deterministic() -> None:
    source_id = node_id_for("Severity 1", NodeType.INCIDENT_SEVERITY)
    target_id = node_id_for("15 minutes", NodeType.TIME_REQUIREMENT)

    assert source_id == node_id_for("Severity 1", NodeType.INCIDENT_SEVERITY)
    assert target_id == node_id_for("15 minutes", NodeType.TIME_REQUIREMENT)
    assert edge_id_for(source_id, target_id, RelationType.HAS_TIME_REQUIREMENT, "chunk-1") == edge_id_for(
        source_id, target_id, RelationType.HAS_TIME_REQUIREMENT, "chunk-1"
    )


def test_graph_store_persists_and_reloads(tmp_path: Path) -> None:
    settings = AppSettings(project_root=tmp_path, data_dir=tmp_path / "data")
    source = GraphNode(
        node_id=node_id_for("Severity 1", NodeType.INCIDENT_SEVERITY),
        label="Severity 1",
        type=NodeType.INCIDENT_SEVERITY,
        source_doc_ids=["it-incident-escalation-sop-v1-0"],
        source_chunk_ids=["chunk-1"],
        mentions=["Severity 1"],
        confidence=0.9,
    )
    target = GraphNode(
        node_id=node_id_for("15 minutes", NodeType.TIME_REQUIREMENT),
        label="15 minutes",
        type=NodeType.TIME_REQUIREMENT,
        source_doc_ids=["it-incident-escalation-sop-v1-0"],
        source_chunk_ids=["chunk-1"],
        mentions=["15 minutes"],
        confidence=0.9,
    )
    edge = GraphEdge(
        edge_id=edge_id_for(source.node_id, target.node_id, RelationType.HAS_TIME_REQUIREMENT, "chunk-1"),
        source_node_id=source.node_id,
        target_node_id=target.node_id,
        relation_type=RelationType.HAS_TIME_REQUIREMENT,
        source_doc_id="it-incident-escalation-sop-v1-0",
        source_chunk_id="chk:it-incident-escalation-sop-v1-0:severity-levels:01:a51d2cb2f1:001",
        evidence_quote="Severity 1 incidents must be acknowledged within 15 minutes.",
        confidence=0.9,
    )

    store = NetworkXGraphStore(settings)
    saved = store.save([source, target], [edge], source_chunk_count=1)
    loaded = store.load()

    assert saved.artifact_path.exists()
    assert loaded.source_chunk_count == 1
    assert [node.node_id for node in loaded.nodes] == [source.node_id, target.node_id]
    assert loaded.edges[0].edge_id == edge.edge_id
    assert loaded.graph.has_edge(source.node_id, target.node_id, key=edge.edge_id)
