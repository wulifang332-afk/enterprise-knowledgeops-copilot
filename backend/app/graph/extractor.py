from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from backend.app.retrieval.corpus import CorpusChunk

from .schema import GraphEdge, GraphExtractionResult, GraphNode, NodeType, RelationType

CREATED_BY = "rule_based_phase4"


@dataclass(frozen=True)
class EntityRule:
    label: str
    type: NodeType
    aliases: tuple[str, ...]


ENTITY_RULES: tuple[EntityRule, ...] = (
    EntityRule("Vendor Payment Request Form", NodeType.FORM, ("Vendor Payment Request Form",)),
    EntityRule("ServiceNow", NodeType.SYSTEM, ("ServiceNow",)),
    EntityRule("Concur Expense", NodeType.SYSTEM, ("Concur Expense",)),
    EntityRule("HRIS", NodeType.SYSTEM, ("HRIS", "HRIS Leave module")),
    EntityRule("Identity Management", NodeType.SYSTEM, ("Identity Management",)),
    EntityRule("Public AI tools", NodeType.SYSTEM, ("Public AI tools", "public AI tools")),
    EntityRule("External SaaS", NodeType.SYSTEM, ("external SaaS", "External SaaS")),
    EntityRule("approved software catalog", NodeType.SYSTEM, ("approved software catalog", "internal software catalog")),
    EntityRule("complaint management system", NodeType.SYSTEM, ("complaint management system",)),
    EntityRule("DPO", NodeType.ROLE, ("DPO", "Data Protection Officer", "Data Protection Office")),
    EntityRule("Finance Operations", NodeType.DEPARTMENT, ("Finance Operations",)),
    EntityRule("Human Resources Operations", NodeType.DEPARTMENT, ("Human Resources Operations",)),
    EntityRule("IT Service Management", NodeType.DEPARTMENT, ("IT Service Management",)),
    EntityRule("Information Security", NodeType.DEPARTMENT, ("Information Security",)),
    EntityRule("Customer Operations", NodeType.DEPARTMENT, ("Customer Operations",)),
    EntityRule("Regional Compliance", NodeType.DEPARTMENT, ("Regional Compliance",)),
    EntityRule("Legal and Compliance", NodeType.DEPARTMENT, ("Legal and Compliance",)),
    EntityRule("Procurement", NodeType.DEPARTMENT, ("Procurement",)),
    EntityRule("Accounts Payable", NodeType.ROLE, ("Accounts Payable",)),
    EntityRule("budget owner", NodeType.ROLE, ("budget owner",)),
    EntityRule("Finance Manager", NodeType.ROLE, ("Finance Manager",)),
    EntityRule("Finance Director", NodeType.ROLE, ("Finance Director",)),
    EntityRule("CFO", NodeType.ROLE, ("CFO",)),
    EntityRule("direct manager", NodeType.ROLE, ("direct manager", "manager")),
    EntityRule("Incident Commander", NodeType.ROLE, ("Incident Commander",)),
    EntityRule("Information Security duty lead", NodeType.ROLE, ("Information Security duty lead",)),
    EntityRule("Customer Operations Director", NodeType.ROLE, ("Customer Operations Director",)),
    EntityRule("Customer Support", NodeType.ROLE, ("Customer Support",)),
    EntityRule("hiring manager", NodeType.ROLE, ("hiring manager",)),
    EntityRule("IT Service Desk", NodeType.ROLE, ("IT Service Desk",)),
    EntityRule("APAC", NodeType.REGION, ("APAC",)),
    EntityRule("EU", NodeType.REGION, ("EU",)),
    EntityRule("Global", NodeType.REGION, ("Global", "globally")),
    EntityRule("Severity 1", NodeType.INCIDENT_SEVERITY, ("Severity 1",)),
    EntityRule("Severity 2", NodeType.INCIDENT_SEVERITY, ("Severity 2",)),
    EntityRule("Severity 3", NodeType.INCIDENT_SEVERITY, ("Severity 3",)),
    EntityRule("customer personal data", NodeType.DATA_TYPE, ("customer personal data", "customer data")),
    EntityRule("employee personal data", NodeType.DATA_TYPE, ("employee personal data", "employee data")),
    EntityRule("government identity numbers", NodeType.DATA_TYPE, ("government identity numbers",)),
    EntityRule("payment details", NodeType.DATA_TYPE, ("payment details",)),
    EntityRule("health information", NodeType.DATA_TYPE, ("health information",)),
    EntityRule("confidential company information", NodeType.DATA_TYPE, ("confidential company information",)),
    EntityRule("confidential regulated business records", NodeType.DATA_TYPE, ("confidential regulated business records",)),
    EntityRule("source code secrets", NodeType.DATA_TYPE, ("source code secrets",)),
    EntityRule("unreleased financial information", NodeType.DATA_TYPE, ("unreleased financial information",)),
    EntityRule("restricted", NodeType.RISK_TYPE, ("restricted", "restricted data")),
    EntityRule("confidential", NodeType.RISK_TYPE, ("confidential",)),
    EntityRule("regulatory breach", NodeType.RISK_TYPE, ("regulatory breach",)),
    EntityRule("privacy impact", NodeType.RISK_TYPE, ("privacy impact",)),
    EntityRule("security compromise", NodeType.RISK_TYPE, ("security compromise",)),
    EntityRule("data-risk event", NodeType.RISK_TYPE, ("data-risk event",)),
    EntityRule("cross-border transfer", NodeType.PROCESS, ("cross-border transfer", "cross-border handling")),
    EntityRule("vendor payment", NodeType.PROCESS, ("vendor payment", "vendor payments")),
    EntityRule("travel reimbursement", NodeType.PROCESS, ("travel reimbursement", "travel claims")),
    EntityRule("employee onboarding", NodeType.PROCESS, ("employee onboarding", "onboarding workflow")),
    EntityRule("incident escalation", NodeType.PROCESS, ("incident escalation", "IT incidents")),
    EntityRule("customer complaint escalation", NodeType.PROCESS, ("customer complaint", "customer complaints")),
    EntityRule("payment release", NodeType.PROCESS, ("payment release",)),
    EntityRule("account provisioning", NodeType.PROCESS, ("account provisioning",)),
    EntityRule("approval process", NodeType.PROCESS, ("approval process", "approval controls")),
    EntityRule("exception process", NodeType.PROCESS, ("exception process", "exceptions")),
    EntityRule("vendor", NodeType.VENDOR, ("vendor", "vendors", "suppliers")),
    EntityRule("customer", NodeType.CUSTOMER, ("customer", "customers")),
)

TIME_PATTERN = re.compile(
    r"\b(?:within |at least |first )?(\d+\s+(?:minutes?|business days?|working days?))\b|\b(first week)\b",
    re.IGNORECASE,
)
THRESHOLD_PATTERN = re.compile(
    r"\bUSD\s+\d{1,3}(?:,\d{3})*(?:\s+and\s+up\s+to\s+USD\s+\d{1,3}(?:,\d{3})*)?"
    r"|\b(?:more than|longer than|above|up to and including)\s+\d+\s+(?:consecutive\s+)?working days\b",
    re.IGNORECASE,
)


class RuleBasedGraphExtractor:
    def extract_chunk(self, record: CorpusChunk) -> GraphExtractionResult:
        nodes: dict[str, GraphNode] = {}
        edges: dict[str, GraphEdge] = {}
        chunk = record.chunk
        metadata = chunk.metadata
        text = chunk.text

        doc_type = NodeType.POLICY if metadata.policy_type.value == "policy" else NodeType.SOP
        doc_node = self._add_node(nodes, metadata.title, doc_type, record, metadata.title, confidence=1.0)

        department_node = self._add_node(nodes, metadata.department, NodeType.DEPARTMENT, record, metadata.department)
        self._add_edge(edges, department_node, doc_node, RelationType.OWNS, record, text)

        owner_node = self._add_node(nodes, metadata.owner, NodeType.DEPARTMENT, record, metadata.owner)
        self._add_edge(edges, owner_node, doc_node, RelationType.OWNS, record, text)

        access_node = self._add_node(
            nodes,
            metadata.access_level.value,
            NodeType.ACCESS_LEVEL,
            record,
            metadata.access_level.value,
            confidence=1.0,
        )
        self._add_edge(edges, doc_node, access_node, RelationType.HAS_ACCESS_LEVEL, record, text)

        for region in metadata.regions:
            region_node = self._add_node(nodes, region, NodeType.REGION, record, region)
            self._add_edge(edges, doc_node, region_node, RelationType.APPLIES_TO, record, text)

        for process in metadata.related_processes:
            process_node = self._add_node(nodes, process, NodeType.PROCESS, record, process)
            self._add_edge(edges, doc_node, process_node, RelationType.GOVERNS, record, text)

        matched: dict[tuple[str, NodeType], GraphNode] = {}
        for rule in ENTITY_RULES:
            alias = first_matching_alias(text, rule.aliases)
            if alias:
                node = self._add_node(nodes, rule.label, rule.type, record, alias)
                matched[(rule.label, rule.type)] = node
                if node.node_id != doc_node.node_id:
                    self._add_edge(edges, doc_node, node, RelationType.MENTIONS, record, text, alias)

        for label in extract_time_requirements(text):
            node = self._add_node(nodes, label, NodeType.TIME_REQUIREMENT, record, label)
            matched[(label, NodeType.TIME_REQUIREMENT)] = node
            self._add_edge(edges, doc_node, node, RelationType.HAS_TIME_REQUIREMENT, record, text, label)

        for label in extract_thresholds(text):
            node = self._add_node(nodes, normalize_space(label), NodeType.THRESHOLD, record, label)
            matched[(node.label, NodeType.THRESHOLD)] = node
            self._add_edge(edges, doc_node, node, RelationType.HAS_THRESHOLD, record, text, label)

        self._extract_specific_relations(edges, record, text, doc_node, matched)
        return GraphExtractionResult(
            nodes=sorted(nodes.values(), key=lambda node: node.node_id),
            edges=sorted(edges.values(), key=lambda edge: edge.edge_id),
        )

    def _extract_specific_relations(
        self,
        edges: dict[str, GraphEdge],
        record: CorpusChunk,
        text: str,
        doc_node: GraphNode,
        matched: dict[tuple[str, NodeType], GraphNode],
    ) -> None:
        form = matched.get(("Vendor Payment Request Form", NodeType.FORM))
        if form and has_any(text, ("must include", "documented in")):
            self._add_edge(edges, doc_node, form, RelationType.REQUIRES, record, text, "Vendor Payment Request Form")

        servicenow = matched.get(("ServiceNow", NodeType.SYSTEM))
        if servicenow and has_any(text, ("reported through ServiceNow", "logs the incident in ServiceNow", "ServiceNow")):
            self._add_edge(edges, doc_node, servicenow, RelationType.USES_SYSTEM, record, text, "ServiceNow")

        severity_1 = matched.get(("Severity 1", NodeType.INCIDENT_SEVERITY))
        time_15 = matched.get(("15 minutes", NodeType.TIME_REQUIREMENT))
        if severity_1 and time_15:
            self._add_edge(edges, severity_1, time_15, RelationType.HAS_TIME_REQUIREMENT, record, text, "15 minutes")

        time_30 = matched.get(("30 minutes", NodeType.TIME_REQUIREMENT))
        if severity_1 and time_30:
            self._add_edge(edges, severity_1, time_30, RelationType.HAS_TIME_REQUIREMENT, record, text, "30 minutes")

        dpo = matched.get(("DPO", NodeType.ROLE))
        if dpo and has_any(text, ("Data Protection Officer approval", "Data Protection Office must approve", "escalates to")):
            self._add_edge(edges, doc_node, dpo, RelationType.ESCALATES_TO, record, text, "Data Protection")

        for label in ("Finance Operations", "Human Resources Operations", "Information Security", "DPO"):
            target = matched.get((label, NodeType.DEPARTMENT)) or matched.get((label, NodeType.ROLE))
            if target and has_any(text, ("requires", "approved by", "must also approve", "must approve")):
                self._add_edge(edges, doc_node, target, RelationType.REQUIRES, record, text, target.label)

        for label in ("cross-border transfer", "vendor payment", "travel reimbursement", "employee onboarding"):
            process = matched.get((label, NodeType.PROCESS))
            if process and has_any(text, ("governs", "defines", "applies to")):
                self._add_edge(edges, doc_node, process, RelationType.GOVERNS, record, text, label)

    def _add_node(
        self,
        nodes: dict[str, GraphNode],
        label: str,
        node_type: NodeType,
        record: CorpusChunk,
        mention: str,
        *,
        confidence: float = 0.9,
    ) -> GraphNode:
        node = GraphNode(
            node_id=node_id_for(label, node_type),
            label=label,
            type=node_type,
            source_doc_ids=[record.chunk.doc_id],
            source_chunk_ids=[record.chunk.chunk_id],
            mentions=[mention],
            confidence=confidence,
            created_by=CREATED_BY,
        )
        existing = nodes.get(node.node_id)
        if existing is None:
            nodes[node.node_id] = node
            return node
        merged = merge_nodes(existing, node)
        nodes[node.node_id] = merged
        return merged

    def _add_edge(
        self,
        edges: dict[str, GraphEdge],
        source: GraphNode,
        target: GraphNode,
        relation_type: RelationType,
        record: CorpusChunk,
        text: str,
        evidence_hint: str | None = None,
        *,
        confidence: float = 0.85,
    ) -> None:
        if relation_type == RelationType.MENTIONS and has_stronger_edge(edges, source, target, record.chunk.chunk_id):
            return
        if relation_type != RelationType.MENTIONS:
            remove_weak_mentions(edges, source, target, record.chunk.chunk_id)
        quote = evidence_quote(text, evidence_hint or target.label)
        edge = GraphEdge(
            edge_id=edge_id_for(source.node_id, target.node_id, relation_type, record.chunk.chunk_id),
            source_node_id=source.node_id,
            target_node_id=target.node_id,
            relation_type=relation_type,
            source_doc_id=record.chunk.doc_id,
            source_chunk_id=record.chunk.chunk_id,
            evidence_quote=quote,
            confidence=confidence,
            created_by=CREATED_BY,
        )
        edges.setdefault(edge.edge_id, edge)


def node_id_for(label: str, node_type: NodeType) -> str:
    type_slug = slugify(node_type.value)
    label_slug = slugify(label)[:80]
    digest = short_hash(f"{node_type.value}|{label.casefold()}")
    return f"node:{type_slug}:{label_slug}:{digest}"


def edge_id_for(source_node_id: str, target_node_id: str, relation_type: RelationType, source_chunk_id: str) -> str:
    digest = short_hash(f"{source_node_id}|{relation_type.value}|{target_node_id}|{source_chunk_id}", length=12)
    return f"edge:{slugify(relation_type.value)}:{digest}"


def has_stronger_edge(
    edges: dict[str, GraphEdge],
    source: GraphNode,
    target: GraphNode,
    source_chunk_id: str,
) -> bool:
    return any(
        edge.source_node_id == source.node_id
        and edge.target_node_id == target.node_id
        and edge.source_chunk_id == source_chunk_id
        and edge.relation_type != RelationType.MENTIONS
        for edge in edges.values()
    )


def remove_weak_mentions(
    edges: dict[str, GraphEdge],
    source: GraphNode,
    target: GraphNode,
    source_chunk_id: str,
) -> None:
    weak_edge_ids = [
        edge_id
        for edge_id, edge in edges.items()
        if edge.source_node_id == source.node_id
        and edge.target_node_id == target.node_id
        and edge.source_chunk_id == source_chunk_id
        and edge.relation_type == RelationType.MENTIONS
    ]
    for edge_id in weak_edge_ids:
        edges.pop(edge_id, None)


def merge_nodes(first: GraphNode, second: GraphNode) -> GraphNode:
    return GraphNode(
        node_id=first.node_id,
        label=first.label,
        type=first.type,
        source_doc_ids=first.source_doc_ids + second.source_doc_ids,
        source_chunk_ids=first.source_chunk_ids + second.source_chunk_ids,
        mentions=first.mentions + second.mentions,
        confidence=max(first.confidence, second.confidence),
        created_by=first.created_by,
    )


def first_matching_alias(text: str, aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        if re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", text, re.IGNORECASE):
            return alias
    return None


def extract_time_requirements(text: str) -> list[str]:
    values: list[str] = []
    for match in TIME_PATTERN.finditer(text):
        value = match.group(1) or match.group(2)
        if value:
            cleaned = normalize_space(value).lower()
            if cleaned == "first week":
                cleaned = "first week"
            values.append(cleaned)
    return dedupe_preserve_case(values)


def extract_thresholds(text: str) -> list[str]:
    return dedupe_preserve_case(normalize_space(match.group(0)) for match in THRESHOLD_PATTERN.finditer(text))


def evidence_quote(text: str, hint: str) -> str:
    compact = normalize_space(text)
    sentences = re.split(r"(?<=[.!?])\s+", compact)
    for sentence in sentences:
        if hint and hint.casefold() in sentence.casefold():
            return sentence[:500]
    return compact[:500]


def has_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.casefold()
    return any(phrase.casefold() in lowered for phrase in phrases)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "value"


def short_hash(value: str, *, length: int = 8) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def dedupe_preserve_case(values) -> list[str]:
    results: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = value.casefold()
        if value and key not in seen:
            results.append(value)
            seen.add(key)
    return results
