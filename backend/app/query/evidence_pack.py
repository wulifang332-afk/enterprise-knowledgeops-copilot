from __future__ import annotations

import re

from backend.app.graph.schema import GraphEdge, GraphNode, RelationType
from backend.app.schemas.retrieval import RetrievalResult

from .schema import GraphEvidence, RetrievalEvidenceItem

EXCERPT_LIMIT = 1200
MAX_MATCHED_NODES = 5
MAX_NEIGHBOR_NODES = 30
MAX_GRAPH_EDGES = 60
PRIORITIZED_RELATION_SCORES = {
    RelationType.USES_SYSTEM: 4.0,
    RelationType.HAS_TIME_REQUIREMENT: 3.5,
    RelationType.ESCALATES_TO: 3.0,
    RelationType.REQUIRES: 2.5,
    RelationType.APPLIES_TO: 2.0,
    RelationType.HAS_THRESHOLD: 1.5,
    RelationType.OWNS: 0.75,
    RelationType.GOVERNS: 0.5,
    RelationType.HAS_ACCESS_LEVEL: 0.25,
    RelationType.RELATED_TO: 0.0,
    RelationType.APPROVES: 0.0,
    RelationType.MENTIONS: -2.0,
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "how",
    "is",
    "of",
    "or",
    "the",
    "to",
    "what",
    "which",
    "who",
    "with",
}


class EvidencePackBuilder:
    def retrieval_items(self, results: list[RetrievalResult]) -> list[RetrievalEvidenceItem]:
        return [
            RetrievalEvidenceItem(
                rank=result.rank,
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                title=result.metadata.title,
                section_title=result.metadata.section_title,
                source_document_metadata=result.metadata,
                bm25_score=result.bm25_score,
                vector_score=result.vector_score,
                hybrid_score=result.hybrid_score,
                citation=result.citation,
                quote=result.citation.quote,
                source_text_excerpt=excerpt(result.text),
            )
            for result in results
        ]

    def graph_evidence(
        self,
        *,
        query: str,
        nodes: list[GraphNode],
        edges: list[GraphEdge],
        depth: int,
        neighborhood_lookup,
        source_doc_ranks: dict[str, int] | None = None,
    ) -> GraphEvidence:
        source_doc_ranks = source_doc_ranks or {}
        source_doc_ids = set(source_doc_ranks)
        matched_nodes = match_nodes(query=query, nodes=nodes, source_doc_ids=source_doc_ids)
        node_by_id: dict[str, GraphNode] = {node.node_id: node for node in nodes}
        evidence_nodes: dict[str, GraphNode] = {node.node_id: node for node in matched_nodes}
        evidence_edges: dict[str, GraphEdge] = {}

        for node in matched_nodes:
            _, neighbors, neighborhood_edges = neighborhood_lookup(node.node_id, depth)
            for neighbor in neighbors:
                evidence_nodes.setdefault(neighbor.node_id, neighbor)
            for edge in neighborhood_edges:
                evidence_edges.setdefault(edge.edge_id, edge)

        if source_doc_ids:
            for edge in edges:
                if edge.source_doc_id in source_doc_ids:
                    evidence_edges.setdefault(edge.edge_id, edge)
                    if edge.source_node_id in node_by_id:
                        evidence_nodes.setdefault(edge.source_node_id, node_by_id[edge.source_node_id])
                    if edge.target_node_id in node_by_id:
                        evidence_nodes.setdefault(edge.target_node_id, node_by_id[edge.target_node_id])

        sorted_edges = rank_edges(
            query=query,
            edges=list(evidence_edges.values()),
            node_by_id=node_by_id,
            source_doc_ranks=source_doc_ranks,
        )[:MAX_GRAPH_EDGES]
        sorted_neighbors = rank_nodes_for_evidence(
            query=query,
            nodes=list(evidence_nodes.values()),
            source_doc_ids=source_doc_ids,
        )[:MAX_NEIGHBOR_NODES]
        return GraphEvidence(
            matched_nodes=matched_nodes,
            neighboring_nodes=sorted_neighbors,
            edges=sorted_edges,
            relation_types=sorted({edge.relation_type.value for edge in sorted_edges}),
        )


def excerpt(value: str, limit: int = EXCERPT_LIMIT) -> str:
    compact = value.strip()
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."


def match_nodes(
    *,
    query: str,
    nodes: list[GraphNode],
    source_doc_ids: set[str] | None = None,
) -> list[GraphNode]:
    normalized_query = normalize(query)
    query_tokens = set(tokens(normalized_query))
    scored: list[tuple[float, str, GraphNode]] = []
    for node in nodes:
        label_normalized = normalize(node.label)
        label_tokens = set(tokens(label_normalized))
        if not label_tokens:
            continue
        overlap = query_tokens.intersection(label_tokens)
        score = len(overlap) / len(label_tokens)
        if label_normalized and label_normalized in normalized_query:
            score += 2.0
        if source_doc_ids and source_doc_ids.intersection(set(node.source_doc_ids)) and (
            overlap or domain_type_matches_query(query_tokens=query_tokens, node=node)
        ):
            score += 0.25
        if domain_type_matches_query(query_tokens=query_tokens, node=node):
            score += 1.25
        if score > 0:
            scored.append((score, node.node_id, node))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [node for _, _, node in scored[:MAX_MATCHED_NODES]]


def rank_edges(
    *,
    query: str,
    edges: list[GraphEdge],
    node_by_id: dict[str, GraphNode],
    source_doc_ranks: dict[str, int],
) -> list[GraphEdge]:
    normalized_query = normalize(query)
    query_tokens = set(tokens(normalized_query))

    def score(edge: GraphEdge) -> tuple[float, str]:
        source = node_by_id.get(edge.source_node_id)
        target = node_by_id.get(edge.target_node_id)
        labels = " ".join(part for part in ((source.label if source else ""), (target.label if target else "")) if part)
        label_tokens = set(tokens(normalize(labels)))
        evidence_tokens = set(tokens(normalize(edge.evidence_quote)))
        query_overlap = len(query_tokens.intersection(label_tokens)) * 2.0
        query_overlap += min(len(query_tokens.intersection(evidence_tokens)), 3) * 0.5
        relation_score = PRIORITIZED_RELATION_SCORES.get(edge.relation_type, 0.0)
        relation_score += query_relation_boost(query_tokens=query_tokens, relation_type=edge.relation_type)
        doc_score = source_document_score(edge.source_doc_id, source_doc_ranks)
        mention_penalty = -3.0 if edge.relation_type == RelationType.MENTIONS else 0.0
        return (query_overlap + relation_score + doc_score + mention_penalty, edge.edge_id)

    ranked = sorted(edges, key=lambda edge: (-score(edge)[0], score(edge)[1]))
    return ranked


def rank_nodes_for_evidence(*, query: str, nodes: list[GraphNode], source_doc_ids: set[str]) -> list[GraphNode]:
    query_tokens = set(tokens(normalize(query)))

    def score(node: GraphNode) -> tuple[float, str]:
        label_tokens = set(tokens(normalize(node.label)))
        overlap = len(query_tokens.intersection(label_tokens))
        doc_overlap = 1 if source_doc_ids.intersection(set(node.source_doc_ids)) else 0
        type_match = 1 if domain_type_matches_query(query_tokens=query_tokens, node=node) else 0
        return (overlap * 2.0 + doc_overlap + type_match, node.node_id)

    return sorted(nodes, key=lambda node: (-score(node)[0], score(node)[1]))


def query_relation_boost(*, query_tokens: set[str], relation_type: RelationType) -> float:
    if relation_type == RelationType.USES_SYSTEM and {"system", "used", "use", "uses"}.intersection(query_tokens):
        return 4.0
    if relation_type == RelationType.HAS_TIME_REQUIREMENT and {"time", "minute", "minutes", "severity", "severities"}.intersection(query_tokens):
        return 2.0
    if relation_type == RelationType.ESCALATES_TO and {"escalate", "escalates", "escalation"}.intersection(query_tokens):
        return 2.0
    if relation_type == RelationType.REQUIRES and {"approval", "approve", "approves", "form", "require", "requires", "required"}.intersection(query_tokens):
        return 2.0
    if relation_type == RelationType.APPLIES_TO and {"apac", "eu", "region", "regions", "cross", "border"}.intersection(query_tokens):
        return 1.5
    return 0.0


def source_document_score(source_doc_id: str, source_doc_ranks: dict[str, int]) -> float:
    if source_doc_id not in source_doc_ranks:
        return 0.0
    rank = source_doc_ranks[source_doc_id]
    return max(0.0, 3.0 - (rank * 0.5))


def domain_type_matches_query(*, query_tokens: set[str], node: GraphNode) -> bool:
    node_type = node.type.value
    if node_type == "System" and {"system", "used", "use", "uses"}.intersection(query_tokens):
        return True
    if node_type == "IncidentSeverity" and {"severity", "incident", "incidents"}.intersection(query_tokens):
        return True
    if node_type == "TimeRequirement" and {"time", "minute", "minutes"}.intersection(query_tokens):
        return True
    if node_type == "Form" and {"form", "approval", "required", "requires"}.intersection(query_tokens):
        return True
    if node_type in {"Policy", "SOP", "Process"} and {"policy", "sop", "process", "workflow", "incident", "incidents"}.intersection(query_tokens):
        return True
    return False


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.casefold())).strip()


def tokens(value: str) -> list[str]:
    output: list[str] = []
    for token in value.split():
        if len(token) <= 2 or token in STOPWORDS:
            continue
        output.append(token)
        if token.endswith("s") and len(token) > 4:
            output.append(token[:-1])
    return output
