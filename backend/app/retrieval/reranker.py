from __future__ import annotations

from typing import Protocol

from backend.app.schemas.retrieval import RetrievalResult


class BaseReranker(Protocol):
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        ...


class NoOpReranker:
    def rerank(self, query: str, results: list[RetrievalResult]) -> list[RetrievalResult]:
        return results

