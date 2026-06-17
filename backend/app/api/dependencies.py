from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from backend.app.core.settings import AppSettings
from backend.app.ingestion.service import IngestionService
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
