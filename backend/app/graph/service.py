from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.retrieval.corpus import ProcessedCorpus
from backend.app.schemas.enums import ErrorCode

from .extractor import RuleBasedGraphExtractor
from .schema import GraphEdge, GraphNode
from .store import GraphSnapshot, NetworkXGraphStore


@dataclass(frozen=True)
class GraphRebuildResult:
    node_count: int
    edge_count: int
    source_chunk_count: int
    artifact_path: str


class GraphService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.extractor = RuleBasedGraphExtractor()
        self.store = NetworkXGraphStore(settings)

    def rebuild(self) -> GraphRebuildResult:
        chunks = ProcessedCorpus(self.settings).load()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        for record in chunks:
            result = self.extractor.extract_chunk(record)
            nodes.extend(result.nodes)
            edges.extend(result.edges)
        snapshot = self.store.save(nodes, edges, source_chunk_count=len(chunks))
        return GraphRebuildResult(
            node_count=len(snapshot.nodes),
            edge_count=len(snapshot.edges),
            source_chunk_count=snapshot.source_chunk_count,
            artifact_path=str(snapshot.artifact_path),
        )

    def nodes(
        self,
        *,
        node_type: str | None = None,
        label_contains: str | None = None,
        source_doc_id: str | None = None,
    ) -> list[GraphNode]:
        snapshot = self.store.load()
        items = snapshot.nodes
        if node_type:
            items = [node for node in items if node.type.value == node_type]
        if label_contains:
            needle = label_contains.casefold()
            items = [node for node in items if needle in node.label.casefold()]
        if source_doc_id:
            items = [node for node in items if source_doc_id in node.source_doc_ids]
        return items

    def edges(
        self,
        *,
        relation_type: str | None = None,
        source_doc_id: str | None = None,
        source_node_id: str | None = None,
        target_node_id: str | None = None,
    ) -> list[GraphEdge]:
        snapshot = self.store.load()
        items = snapshot.edges
        if relation_type:
            items = [edge for edge in items if edge.relation_type.value == relation_type]
        if source_doc_id:
            items = [edge for edge in items if edge.source_doc_id == source_doc_id]
        if source_node_id:
            items = [edge for edge in items if edge.source_node_id == source_node_id]
        if target_node_id:
            items = [edge for edge in items if edge.target_node_id == target_node_id]
        return items

    def neighborhood(self, *, node_id: str, depth: int = 1) -> tuple[GraphNode, list[GraphNode], list[GraphEdge]]:
        if depth < 1 or depth > 2:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_REQUEST,
                "Graph neighborhood depth must be between 1 and 2.",
                {"depth": depth, "max_depth": 2},
            )
        snapshot = self.store.load()
        node_by_id = {node.node_id: node for node in snapshot.nodes}
        if node_id not in node_by_id:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_REQUEST,
                "Graph node was not found.",
                {"node_id": node_id},
            )
        selected_ids = neighborhood_node_ids(snapshot, node_id=node_id, depth=depth)
        nodes = [node for node in snapshot.nodes if node.node_id in selected_ids]
        edges = [
            edge
            for edge in snapshot.edges
            if edge.source_node_id in selected_ids and edge.target_node_id in selected_ids
        ]
        return node_by_id[node_id], nodes, edges

    def snapshot(self) -> GraphSnapshot:
        return self.store.load()


def neighborhood_node_ids(snapshot: GraphSnapshot, *, node_id: str, depth: int) -> set[str]:
    undirected = snapshot.graph.to_undirected(as_view=True)
    lengths = nx.single_source_shortest_path_length(undirected, node_id, cutoff=depth)
    return set(lengths)
