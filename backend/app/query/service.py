from __future__ import annotations

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.graph.service import GraphService
from backend.app.retrieval.service import RetrievalSearchService
from backend.app.schemas.enums import ErrorCode

from .classifier import RuleBasedQueryClassifier
from .evidence_pack import EvidencePackBuilder
from .router import QueryRouter
from .schema import EvidencePack, EvidencePackStatus, GraphEvidence, QueryRequest

PHASE_5A_LIMITATION = "Phase 5A returns evidence packs only. It does not generate final natural-language answers."


class QueryPlanningService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.classifier = RuleBasedQueryClassifier()
        self.router = QueryRouter()
        self.retrieval_service = RetrievalSearchService(settings)
        self.graph_service = GraphService(settings)
        self.builder = EvidencePackBuilder()

    def plan(self, *, request: QueryRequest, request_id: str) -> EvidencePack:
        intent = self.classifier.classify(request.query)
        decision = self.router.route(request=request, intent=intent)
        limitations = [PHASE_5A_LIMITATION]

        if decision.refusal_reason:
            return EvidencePack(
                request_id=request_id,
                query=request.query,
                intent=decision.intent,
                route=decision.route,
                status=EvidencePackStatus.REFUSED,
                refusal_reason=decision.refusal_reason,
                limitations=limitations + [decision.reason],
            )

        retrieval_results = []
        degraded = False
        if decision.include_retrieval:
            outcome = self.retrieval_service.search(
                query=request.query,
                retrieval_mode=decision.retrieval_mode,
                top_k=request.top_k,
                filters=decision.filters.active_dict(),
            )
            retrieval_results = outcome.results
            if outcome.degraded:
                degraded = True
                limitations.extend(outcome.degraded_reasons)
            if not outcome.results:
                limitations.append("No retrieval evidence matched the query and active filters.")

        retrieval_evidence = self.builder.retrieval_items(retrieval_results)
        graph_evidence = GraphEvidence()

        if decision.include_graph:
            try:
                snapshot = self.graph_service.snapshot()
                graph_evidence = self.builder.graph_evidence(
                    query=request.query,
                    nodes=snapshot.nodes,
                    edges=snapshot.edges,
                    depth=decision.graph_depth,
                    source_doc_ranks=source_doc_ranks(retrieval_results),
                    neighborhood_lookup=self._neighborhood_lookup,
                )
                if not graph_evidence.matched_nodes and not graph_evidence.edges:
                    limitations.append("No graph evidence matched the query.")
            except KnowledgeOpsError as exc:
                if exc.error_code != ErrorCode.GRAPH_UNAVAILABLE:
                    raise
                degraded = True
                limitations.append("Graph evidence is unavailable. Rebuild the graph before using graph context.")

        status = EvidencePackStatus.DEGRADED if degraded else EvidencePackStatus.EVIDENCE_READY
        return EvidencePack(
            request_id=request_id,
            query=request.query,
            intent=decision.intent,
            route=decision.route,
            status=status,
            retrieval_evidence=retrieval_evidence,
            graph_evidence=graph_evidence,
            citations=[item.citation for item in retrieval_evidence],
            refusal_reason=None,
            limitations=limitations,
        )

    def _neighborhood_lookup(self, node_id: str, depth: int):
        return self.graph_service.neighborhood(node_id=node_id, depth=depth)


def source_doc_ranks(results) -> dict[str, int]:
    ranks: dict[str, int] = {}
    for result in results:
        ranks.setdefault(result.doc_id, result.rank)
    return ranks
