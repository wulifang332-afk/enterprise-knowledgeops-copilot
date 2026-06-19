from __future__ import annotations

from backend.app.schemas.api import SearchFilters

from .schema import QueryIntent, QueryRequest, QueryRoute, RefusalReason, RouteDecision


class QueryRouter:
    def route(self, *, request: QueryRequest, intent: QueryIntent) -> RouteDecision:
        merged_filters = SearchFilters.model_validate(request.filters.model_dump())
        if intent == QueryIntent.OUT_OF_SCOPE:
            return RouteDecision(
                intent=intent,
                route=QueryRoute.STRUCTURED_REFUSAL,
                confidence=0.95,
                include_retrieval=False,
                include_graph=False,
                filters=merged_filters,
                refusal_reason=RefusalReason.OUT_OF_SCOPE,
                reason="The query is outside the synthetic enterprise policy and operations corpus.",
            )
        if intent == QueryIntent.UNSUPPORTED:
            return RouteDecision(
                intent=intent,
                route=QueryRoute.STRUCTURED_REFUSAL,
                confidence=0.9,
                include_retrieval=False,
                include_graph=False,
                filters=merged_filters,
                refusal_reason=RefusalReason.UNSUPPORTED_IN_PHASE_5A,
                reason=(
                    "This request asks for unsupported free-form answer drafting. "
                    "Use generate_answer=true with an enterprise question for governed citation-grounded answers."
                ),
            )
        if intent == QueryIntent.FACT_LOOKUP:
            return RouteDecision(
                intent=intent,
                route=QueryRoute.HYBRID_RETRIEVAL,
                confidence=0.72,
                include_retrieval=True,
                include_graph=False,
                filters=merged_filters,
                reason="Fact lookup uses hybrid retrieval and citation-backed chunks.",
            )
        if intent == QueryIntent.POLICY_LOOKUP:
            merged_filters.policy_types = merged_filters.policy_types or ["policy"]
            return RouteDecision(
                intent=intent,
                route=QueryRoute.HYBRID_RETRIEVAL_WITH_POLICY_FILTERS,
                confidence=0.82,
                include_retrieval=True,
                include_graph=request.include_graph,
                graph_depth=1,
                filters=merged_filters,
                reason="Policy lookup uses hybrid retrieval with policy metadata filters and optional graph evidence.",
            )
        if intent == QueryIntent.PROCESS_LOOKUP:
            return RouteDecision(
                intent=intent,
                route=QueryRoute.HYBRID_RETRIEVAL_WITH_GRAPH_CONTEXT,
                confidence=0.82,
                include_retrieval=True,
                include_graph=request.include_graph,
                graph_depth=1,
                filters=merged_filters,
                reason="Process lookup uses hybrid retrieval and graph neighborhoods around detected process entities.",
            )
        if intent == QueryIntent.MULTI_HOP:
            return RouteDecision(
                intent=intent,
                route=QueryRoute.HYBRID_RETRIEVAL_WITH_GRAPH_CONTEXT,
                confidence=0.86,
                include_retrieval=True,
                include_graph=request.include_graph,
                graph_depth=2,
                filters=merged_filters,
                reason="Multi-hop planning combines hybrid retrieval with depth-2 graph neighborhood evidence.",
            )
        return RouteDecision(
            intent=intent,
            route=QueryRoute.GRAPH_NEIGHBORHOOD,
            confidence=0.84,
            include_retrieval=False,
            include_graph=True,
            graph_depth=1,
            filters=merged_filters,
            reason="Graph exploration uses graph node matching and neighborhood evidence without answer synthesis.",
        )
