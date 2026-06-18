from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import networkx as nx

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode

from .extractor import merge_nodes
from .schema import GraphArtifact, GraphEdge, GraphNode, RelationType

DOCUMENT_LEVEL_RELATIONS = {
    RelationType.OWNS,
    RelationType.APPLIES_TO,
    RelationType.HAS_ACCESS_LEVEL,
    RelationType.GOVERNS,
}


@dataclass(frozen=True)
class GraphSnapshot:
    graph: nx.MultiDiGraph
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    source_chunk_count: int
    artifact_path: Path


class NetworkXGraphStore:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.artifact_path = self.settings.graph_dir / "knowledge_graph.json"

    def save(self, nodes: list[GraphNode], edges: list[GraphEdge], *, source_chunk_count: int) -> GraphSnapshot:
        self.settings.graph_dir.mkdir(parents=True, exist_ok=True)
        merged_nodes = merge_node_list(nodes)
        merged_edges = merge_edge_list(edges)
        artifact = GraphArtifact(nodes=merged_nodes, edges=merged_edges, source_chunk_count=source_chunk_count)
        tmp_path = self.artifact_path.with_suffix(".json.tmp")
        tmp_path.write_text(json.dumps(artifact.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.artifact_path)
        return self._snapshot_from_artifact(artifact)

    def load(self) -> GraphSnapshot:
        if not self.artifact_path.exists():
            raise KnowledgeOpsError(
                ErrorCode.GRAPH_UNAVAILABLE,
                "Graph artifact is unavailable. Rebuild the graph first.",
                {"artifact_path": str(self.artifact_path)},
            )
        payload = json.loads(self.artifact_path.read_text(encoding="utf-8"))
        artifact = GraphArtifact.model_validate(payload)
        return self._snapshot_from_artifact(artifact)

    def _snapshot_from_artifact(self, artifact: GraphArtifact) -> GraphSnapshot:
        graph = nx.MultiDiGraph()
        for node in artifact.nodes:
            graph.add_node(node.node_id, **node.model_dump(mode="json"))
        for edge in artifact.edges:
            graph.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                key=edge.edge_id,
                **edge.model_dump(mode="json"),
            )
        return GraphSnapshot(
            graph=graph,
            nodes=sorted(artifact.nodes, key=lambda node: node.node_id),
            edges=sorted(artifact.edges, key=lambda edge: edge.edge_id),
            source_chunk_count=artifact.source_chunk_count,
            artifact_path=self.artifact_path,
        )


def merge_node_list(nodes: list[GraphNode]) -> list[GraphNode]:
    by_id: dict[str, GraphNode] = {}
    for node in nodes:
        existing = by_id.get(node.node_id)
        by_id[node.node_id] = merge_nodes(existing, node) if existing else node
    return sorted(by_id.values(), key=lambda node: node.node_id)


def merge_edge_list(edges: list[GraphEdge]) -> list[GraphEdge]:
    by_key: dict[tuple[str, ...], GraphEdge] = {}
    strong_pairs = {
        (edge.source_node_id, edge.target_node_id, edge.source_doc_id)
        for edge in edges
        if edge.relation_type != RelationType.MENTIONS
    }
    for edge in sorted(
        edges,
        key=lambda item: (
            item.source_doc_id,
            item.source_chunk_id,
            item.relation_type.value,
            item.source_node_id,
            item.target_node_id,
            item.edge_id,
        ),
    ):
        if edge.relation_type == RelationType.MENTIONS and (
            edge.source_node_id,
            edge.target_node_id,
            edge.source_doc_id,
        ) in strong_pairs:
            continue
        key = semantic_edge_key(edge)
        by_key.setdefault(key, edge)
    return sorted(by_key.values(), key=lambda edge: edge.edge_id)


def semantic_edge_key(edge: GraphEdge) -> tuple[str, ...]:
    if edge.relation_type in DOCUMENT_LEVEL_RELATIONS:
        return (
            "document",
            edge.source_node_id,
            edge.relation_type.value,
            edge.target_node_id,
            edge.source_doc_id,
        )
    return ("edge", edge.edge_id)
