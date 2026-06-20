from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from backend.app.core.settings import AppSettings
from backend.app.evaluation.service import EvaluationService
from backend.app.graph.service import GraphService
from backend.app.ingestion.service import IngestionService
from backend.app.query.service import QueryPlanningService
from backend.app.retrieval.indexing import IndexRebuildService
from backend.app.retrieval.service import RetrievalSearchService


@lru_cache
def get_settings() -> AppSettings:
    return AppSettings()


def get_ingestion_service(settings: AppSettings = Depends(get_settings)) -> IngestionService:
    return IngestionService(settings=settings)


def get_index_rebuild_service(settings: AppSettings = Depends(get_settings)) -> IndexRebuildService:
    return IndexRebuildService(settings)


def get_retrieval_search_service(settings: AppSettings = Depends(get_settings)) -> RetrievalSearchService:
    return RetrievalSearchService(settings)


def get_graph_service(settings: AppSettings = Depends(get_settings)) -> GraphService:
    return GraphService(settings)


def get_query_planning_service(settings: AppSettings = Depends(get_settings)) -> QueryPlanningService:
    return QueryPlanningService(settings)


def get_evaluation_service(settings: AppSettings = Depends(get_settings)) -> EvaluationService:
    return EvaluationService(settings)
