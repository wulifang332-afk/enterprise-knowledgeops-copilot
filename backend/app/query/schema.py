from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from backend.app.graph.schema import GraphEdge, GraphNode
from backend.app.schemas.api import SearchFilters
from backend.app.schemas.documents import ChunkMetadata, StrictBaseModel
from backend.app.schemas.retrieval import Citation


class QueryIntent(StrEnum):
    FACT_LOOKUP = "fact_lookup"
    POLICY_LOOKUP = "policy_lookup"
    PROCESS_LOOKUP = "process_lookup"
    MULTI_HOP = "multi_hop"
    GRAPH_EXPLORATION = "graph_exploration"
    OUT_OF_SCOPE = "out_of_scope"
    UNSUPPORTED = "unsupported"


class QueryRoute(StrEnum):
    HYBRID_RETRIEVAL = "hybrid_retrieval"
    HYBRID_RETRIEVAL_WITH_POLICY_FILTERS = "hybrid_retrieval_with_policy_filters"
    HYBRID_RETRIEVAL_WITH_GRAPH_CONTEXT = "hybrid_retrieval_with_graph_context"
    GRAPH_NEIGHBORHOOD = "graph_neighborhood"
    STRUCTURED_REFUSAL = "structured_refusal"


class EvidencePackStatus(StrEnum):
    EVIDENCE_READY = "evidence_ready"
    DEGRADED = "degraded"
    REFUSED = "refused"


class RefusalReason(StrEnum):
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    UNSUPPORTED_IN_PHASE_5A = "UNSUPPORTED_IN_PHASE_5A"


class QueryRequest(StrictBaseModel):
    query: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    include_graph: bool = True
    filters: SearchFilters = Field(default_factory=SearchFilters)


class RouteDecision(StrictBaseModel):
    intent: QueryIntent
    route: QueryRoute
    confidence: float = Field(ge=0.0, le=1.0)
    retrieval_mode: Literal["hybrid"] = "hybrid"
    include_retrieval: bool
    include_graph: bool
    graph_depth: int = Field(default=1, ge=1, le=2)
    filters: SearchFilters = Field(default_factory=SearchFilters)
    refusal_reason: RefusalReason | None = None
    reason: str = Field(min_length=1, max_length=500)


class RetrievalEvidenceItem(StrictBaseModel):
    rank: int = Field(ge=1)
    chunk_id: str
    doc_id: str
    title: str
    section_title: str
    source_document_metadata: ChunkMetadata
    bm25_score: float | None = Field(default=None, ge=0.0, le=1.0)
    vector_score: float | None = Field(default=None, ge=0.0, le=1.0)
    hybrid_score: float = Field(ge=0.0, le=1.0)
    citation: Citation
    quote: str = Field(min_length=1)
    source_text_excerpt: str = Field(min_length=1)


class GraphEvidence(StrictBaseModel):
    matched_nodes: list[GraphNode] = Field(default_factory=list)
    neighboring_nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    relation_types: list[str] = Field(default_factory=list)


class EvidencePack(StrictBaseModel):
    request_id: str
    query: str
    intent: QueryIntent
    route: QueryRoute
    status: EvidencePackStatus
    retrieval_evidence: list[RetrievalEvidenceItem] = Field(default_factory=list)
    graph_evidence: GraphEvidence = Field(default_factory=GraphEvidence)
    citations: list[Citation] = Field(default_factory=list)
    refusal_reason: RefusalReason | None = None
    limitations: list[str] = Field(default_factory=list)
    next_phase_note: str = "Final answer generation is planned for Phase 5B."

