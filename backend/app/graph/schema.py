from __future__ import annotations

from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from backend.app.schemas.documents import ID_PATTERN, StrictBaseModel


class NodeType(StrEnum):
    POLICY = "Policy"
    SOP = "SOP"
    DOCUMENT = "Document"
    DEPARTMENT = "Department"
    REGION = "Region"
    ROLE = "Role"
    SYSTEM = "System"
    FORM = "Form"
    APPROVAL_LEVEL = "ApprovalLevel"
    RISK_TYPE = "RiskType"
    DATA_TYPE = "DataType"
    PROCESS = "Process"
    THRESHOLD = "Threshold"
    TIME_REQUIREMENT = "TimeRequirement"
    VENDOR = "Vendor"
    CUSTOMER = "Customer"
    INCIDENT_SEVERITY = "IncidentSeverity"
    ACCESS_LEVEL = "AccessLevel"


class RelationType(StrEnum):
    REQUIRES = "REQUIRES"
    APPROVES = "APPROVES"
    OWNS = "OWNS"
    APPLIES_TO = "APPLIES_TO"
    ESCALATES_TO = "ESCALATES_TO"
    USES_SYSTEM = "USES_SYSTEM"
    HAS_THRESHOLD = "HAS_THRESHOLD"
    HAS_TIME_REQUIREMENT = "HAS_TIME_REQUIREMENT"
    HAS_ACCESS_LEVEL = "HAS_ACCESS_LEVEL"
    RELATED_TO = "RELATED_TO"
    GOVERNS = "GOVERNS"
    MENTIONS = "MENTIONS"


class GraphNode(StrictBaseModel):
    node_id: str = Field(pattern=ID_PATTERN)
    label: str = Field(min_length=1, max_length=200)
    type: NodeType
    source_doc_ids: list[str] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)
    mentions: list[str] = Field(default_factory=list, max_length=50)
    confidence: float = Field(ge=0.0, le=1.0)
    created_by: str = Field(default="rule_based_phase4", min_length=1, max_length=80)

    @field_validator("source_doc_ids", "source_chunk_ids", "mentions")
    @classmethod
    def dedupe_strings(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for item in value:
            stripped = item.strip()
            if stripped and stripped not in seen:
                cleaned.append(stripped)
                seen.add(stripped)
        return sorted(cleaned)


class GraphEdge(StrictBaseModel):
    edge_id: str = Field(pattern=ID_PATTERN)
    source_node_id: str = Field(pattern=ID_PATTERN)
    target_node_id: str = Field(pattern=ID_PATTERN)
    relation_type: RelationType
    source_doc_id: str = Field(pattern=ID_PATTERN)
    source_chunk_id: str = Field(pattern=ID_PATTERN)
    evidence_quote: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0)
    created_by: str = Field(default="rule_based_phase4", min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_edge_direction(self) -> "GraphEdge":
        if self.source_node_id == self.target_node_id:
            raise ValueError("source_node_id and target_node_id must differ")
        return self


class GraphExtractionResult(StrictBaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class GraphArtifact(StrictBaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    source_chunk_count: int = Field(ge=0)


class GraphRebuildResponse(StrictBaseModel):
    request_id: str
    node_count: int = Field(ge=0)
    edge_count: int = Field(ge=0)
    source_chunk_count: int = Field(ge=0)
    artifact_path: str


class GraphNodeListResponse(StrictBaseModel):
    request_id: str
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    items: list[GraphNode]


class GraphEdgeListResponse(StrictBaseModel):
    request_id: str
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(ge=1)
    items: list[GraphEdge]


class GraphNeighborhoodResponse(StrictBaseModel):
    request_id: str
    node_id: str = Field(pattern=ID_PATTERN)
    depth: int = Field(ge=1, le=2)
    selected_node: GraphNode
    nodes: list[GraphNode]
    edges: list[GraphEdge]
