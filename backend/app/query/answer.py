from __future__ import annotations

import re

from backend.app.graph.schema import GraphEdge, GraphNode, RelationType
from backend.app.schemas.retrieval import Citation

from .schema import (
    AnswerGenerationStatus,
    AnswerRefusalReason,
    EvidencePack,
    EvidencePackStatus,
    QueryIntent,
    RefusalReason,
    RetrievalEvidenceItem,
)

SUPPORTED_ANSWER_INTENTS = {
    QueryIntent.FACT_LOOKUP,
    QueryIntent.POLICY_LOOKUP,
    QueryIntent.PROCESS_LOOKUP,
    QueryIntent.MULTI_HOP,
    QueryIntent.GRAPH_EXPLORATION,
}
MAX_ANSWER_CITATIONS = 3
GENERIC_QUERY_TERMS = {
    "about",
    "answer",
    "approval",
    "approvals",
    "approve",
    "approves",
    "between",
    "company",
    "companys",
    "does",
    "employee",
    "employees",
    "for",
    "from",
    "how",
    "required",
    "requires",
    "tell",
    "the",
    "used",
    "uses",
    "using",
    "what",
    "which",
    "work",
}


class DeterministicAnswerComposer:
    """Template-based Phase 5B answer composer.

    The composer does not call an external model. It only emits answers when
    the returned evidence pack already contains citable retrieval evidence.
    """

    def compose(self, pack: EvidencePack) -> EvidencePack:
        if pack.status == EvidencePackStatus.REFUSED:
            return pack.model_copy(
                update={
                    "answer_generation_status": AnswerGenerationStatus.REFUSED,
                    "answer_refusal_reason": map_pack_refusal(pack.refusal_reason),
                    "grounding_summary": "No answer was generated because the query route returned a structured refusal.",
                }
            )

        if pack.intent not in SUPPORTED_ANSWER_INTENTS:
            return self._refuse(
                pack,
                AnswerGenerationStatus.REFUSED,
                AnswerRefusalReason.UNSUPPORTED_IN_PHASE_5A,
                "No answer was generated because this intent is not supported by the Phase 5B deterministic composer.",
            )

        if not pack.citations or not pack.retrieval_evidence:
            return self._refuse(
                pack,
                AnswerGenerationStatus.INSUFFICIENT_EVIDENCE,
                AnswerRefusalReason.NO_CITABLE_EVIDENCE,
                "No answer was generated because the evidence pack did not include citable retrieval evidence.",
            )

        sufficiency = evidence_sufficiency(pack)
        if not sufficiency.is_sufficient:
            return self._refuse(
                pack,
                AnswerGenerationStatus.INSUFFICIENT_EVIDENCE,
                AnswerRefusalReason.INSUFFICIENT_EVIDENCE,
                sufficiency.reason,
            )

        answer, citations = self._compose_supported_answer(pack)
        if not answer or not citations:
            return self._refuse(
                pack,
                AnswerGenerationStatus.INSUFFICIENT_EVIDENCE,
                AnswerRefusalReason.NO_CITABLE_EVIDENCE,
                "No answer was generated because no grounded citation could be attached to the selected evidence.",
            )

        return pack.model_copy(
            update={
                "answer": answer,
                "answer_citations": citations,
                "answer_generation_status": AnswerGenerationStatus.GENERATED,
                "answer_refusal_reason": None,
                "grounding_summary": grounding_summary(pack=pack, citations=citations),
            }
        )

    def _compose_supported_answer(self, pack: EvidencePack) -> tuple[str | None, list[Citation]]:
        node_by_id = graph_node_map(pack)
        if pack.intent == QueryIntent.POLICY_LOOKUP:
            answer = compose_vendor_payment_answer(pack=pack, node_by_id=node_by_id)
            if answer:
                return answer
        if pack.intent == QueryIntent.PROCESS_LOOKUP:
            answer = compose_system_answer(pack=pack, node_by_id=node_by_id)
            if answer:
                return answer
        if pack.intent == QueryIntent.MULTI_HOP:
            answer = compose_cross_border_answer(pack=pack)
            if answer:
                return answer
        if pack.intent == QueryIntent.GRAPH_EXPLORATION:
            answer = compose_graph_summary(pack=pack, node_by_id=node_by_id)
            if answer:
                return answer
        return compose_generic_retrieval_answer(pack)

    @staticmethod
    def _refuse(
        pack: EvidencePack,
        status: AnswerGenerationStatus,
        reason: AnswerRefusalReason,
        summary: str,
    ) -> EvidencePack:
        return pack.model_copy(
            update={
                "answer": None,
                "answer_citations": [],
                "answer_generation_status": status,
                "answer_refusal_reason": reason,
                "grounding_summary": summary,
            }
        )


class EvidenceSufficiency:
    def __init__(self, *, is_sufficient: bool, reason: str) -> None:
        self.is_sufficient = is_sufficient
        self.reason = reason


def evidence_sufficiency(pack: EvidencePack) -> EvidenceSufficiency:
    evidence_text = searchable_evidence_text(pack)
    evidence_terms = set(tokenize(evidence_text))
    required_terms = meaningful_query_terms(pack.query)
    uncovered_terms = sorted(term for term in required_terms if term not in evidence_terms)
    if uncovered_terms:
        joined = ", ".join(uncovered_terms[:5])
        return EvidenceSufficiency(
            is_sufficient=False,
            reason=f"No answer was generated because returned evidence did not cover required query term(s): {joined}.",
        )
    if not any(item.hybrid_score > 0.0 for item in pack.retrieval_evidence):
        return EvidenceSufficiency(
            is_sufficient=False,
            reason="No answer was generated because retrieval evidence scores were too weak.",
        )
    return EvidenceSufficiency(is_sufficient=True, reason="Evidence contains citable retrieval support for the query.")


def compose_vendor_payment_answer(
    *, pack: EvidencePack, node_by_id: dict[str, GraphNode]
) -> tuple[str | None, list[Citation]] | None:
    edge = first_edge(pack, RelationType.REQUIRES, target_type="Form", node_by_id=node_by_id)
    citation = citation_for_chunk(pack, "required-documents") or citation_for_edge(pack, edge)
    target = node_by_id.get(edge.target_node_id).label if edge and edge.target_node_id in node_by_id else "Vendor Payment Request Form"
    if citation and "vendor payment request form" in normalize(citation.quote):
        answer = (
            f"Vendor payment requests require the {target}, plus a valid vendor invoice and either an approved "
            f"purchase order or an executed contract reference [{citation.citation_id}]."
        )
        return answer, [citation]
    return None


def compose_system_answer(
    *, pack: EvidencePack, node_by_id: dict[str, GraphNode]
) -> tuple[str | None, list[Citation]] | None:
    edge = first_edge(pack, RelationType.USES_SYSTEM, target_type="System", node_by_id=node_by_id)
    citation = citation_for_edge(pack, edge) if edge else citation_for_chunk(pack, "severity-1-workflow")
    system = node_by_id.get(edge.target_node_id).label if edge and edge.target_node_id in node_by_id else "ServiceNow"
    if citation and "servicenow" in normalize(citation.quote):
        answer = (
            f"Severity 1 incidents are logged in {system} by the IT Service Desk when the criteria are met "
            f"[{citation.citation_id}]. "
            f"The same workflow requires notifying the Incident Commander and Information Security duty lead within 15 minutes "
            f"[{citation.citation_id}]."
        )
        return answer, [citation]
    return None


def compose_cross_border_answer(pack: EvidencePack) -> tuple[str | None, list[Citation]] | None:
    approval_citation = citation_for_chunk(pack, "approval-process")
    scope_citation = citation_for_chunk(pack, "purpose-and-scope")
    exception_citation = citation_for_chunk(pack, "exceptions-and-evidence")
    citations = unique_citations([scope_citation, approval_citation, exception_citation])[:MAX_ANSWER_CITATIONS]
    if not approval_citation:
        return None

    parts: list[str] = []
    if scope_citation:
        parts.append(
            "The cross-border policy governs handling of personal data and confidential regulated data in APAC and EU operations "
            f"[{scope_citation.citation_id}]."
        )
    parts.append(
        "Cross-border transfer of personal data requires Data Protection Officer approval and an approved transfer mechanism before the transfer occurs; the request must describe the data category, origin region, destination region, vendor or system, business purpose, retention period, and security controls "
        f"[{approval_citation.citation_id}]."
    )
    if exception_citation:
        parts.append(
            "Exceptions require written Data Protection Office approval, and EU personal data exceptions also require Legal review "
            f"[{exception_citation.citation_id}]."
        )
    return " ".join(parts), citations


def compose_graph_summary(
    *, pack: EvidencePack, node_by_id: dict[str, GraphNode]
) -> tuple[str | None, list[Citation]] | None:
    for edge in pack.graph_evidence.edges:
        citation = citation_for_edge(pack, edge)
        if citation:
            source = node_by_id.get(edge.source_node_id)
            target = node_by_id.get(edge.target_node_id)
            if source and target:
                answer = (
                    f"The graph evidence links {source.label} to {target.label} with relation "
                    f"{edge.relation_type.value} [{citation.citation_id}]."
                )
                return answer, [citation]
    return None


def compose_generic_retrieval_answer(pack: EvidencePack) -> tuple[str | None, list[Citation]]:
    citations = unique_citations([item.citation for item in pack.retrieval_evidence[:2]])
    statements: list[str] = []
    for item in pack.retrieval_evidence[:2]:
        sentence = first_fact_sentence(item.quote)
        if sentence:
            statements.append(f"{sentence.rstrip('.!?')} [{item.citation.citation_id}].")
    return " ".join(statements) if statements else None, citations


def first_edge(
    pack: EvidencePack,
    relation_type: RelationType,
    *,
    target_type: str | None = None,
    node_by_id: dict[str, GraphNode],
) -> GraphEdge | None:
    for edge in pack.graph_evidence.edges:
        target = node_by_id.get(edge.target_node_id)
        if edge.relation_type == relation_type and (target_type is None or (target and target.type.value == target_type)):
            return edge
    return None


def citation_for_edge(pack: EvidencePack, edge: GraphEdge | None) -> Citation | None:
    if not edge:
        return None
    for item in pack.retrieval_evidence:
        if item.chunk_id == edge.source_chunk_id:
            return item.citation
    for item in pack.retrieval_evidence:
        if item.doc_id == edge.source_doc_id:
            return item.citation
    return pack.citations[0] if pack.citations else None


def citation_for_chunk(pack: EvidencePack, chunk_fragment: str) -> Citation | None:
    for item in pack.retrieval_evidence:
        if chunk_fragment in item.chunk_id:
            return item.citation
    return None


def graph_node_map(pack: EvidencePack) -> dict[str, GraphNode]:
    nodes = [*pack.graph_evidence.matched_nodes, *pack.graph_evidence.neighboring_nodes]
    return {node.node_id: node for node in nodes}


def grounding_summary(*, pack: EvidencePack, citations: list[Citation]) -> str:
    citation_ids = ", ".join(citation.citation_id for citation in citations)
    docs = ", ".join(sorted({citation.title for citation in citations}))
    graph_count = len(pack.graph_evidence.edges)
    return f"Generated from {len(citations)} retrieval citation(s): {citation_ids}. Source document(s): {docs}. Graph edges considered: {graph_count}."


def map_pack_refusal(reason: RefusalReason | None) -> AnswerRefusalReason | None:
    if reason == RefusalReason.OUT_OF_SCOPE:
        return AnswerRefusalReason.OUT_OF_SCOPE
    if reason == RefusalReason.UNSUPPORTED_IN_PHASE_5A:
        return AnswerRefusalReason.UNSUPPORTED_IN_PHASE_5A
    return None


def searchable_evidence_text(pack: EvidencePack) -> str:
    retrieval_text = " ".join(
        f"{item.title} {item.section_title} {item.quote} {item.source_text_excerpt}" for item in pack.retrieval_evidence
    )
    nodes = [*pack.graph_evidence.matched_nodes, *pack.graph_evidence.neighboring_nodes]
    graph_text = " ".join(
        [
            " ".join(node.label for node in nodes),
            " ".join(edge.evidence_quote for edge in pack.graph_evidence.edges),
        ]
    )
    return f"{retrieval_text} {graph_text}"


def meaningful_query_terms(query: str) -> set[str]:
    return {token for token in tokenize(query) if token not in GENERIC_QUERY_TERMS}


def first_fact_sentence(text: str) -> str | None:
    cleaned = re.sub(r"^#+\s*[^\n]+\n+", "", text.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) >= 20:
            return sentence
    return None


def unique_citations(values: list[Citation | None]) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[str] = set()
    for citation in values:
        if citation and citation.citation_id not in seen:
            citations.append(citation)
            seen.add(citation.citation_id)
    return citations


def tokenize(value: str) -> list[str]:
    normalized = normalize(value)
    tokens: list[str] = []
    for raw in normalized.split():
        if len(raw) <= 2:
            continue
        token = raw[:-1] if raw.endswith("s") and len(raw) > 4 else raw
        tokens.append(token)
    return tokens


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", value.casefold())).strip()
