from __future__ import annotations

from dataclasses import dataclass

from backend.app.citations.builder import CitationBuilder
from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.retrieval import RetrievalResult

from .bm25 import BM25Index
from .corpus import ProcessedCorpus
from .hybrid import HybridRetriever
from .types import RetrieverCandidate
from .vector import ChromaVectorIndex


@dataclass(frozen=True)
class SearchOutcome:
    results: list[RetrievalResult]
    degraded: bool
    degraded_reasons: list[str]


class RetrievalSearchService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.corpus_by_id = ProcessedCorpus(settings).by_chunk_id()
        self.citation_builder = CitationBuilder()

    def search(
        self,
        *,
        query: str,
        retrieval_mode: str,
        top_k: int,
        filters: dict | None = None,
    ) -> SearchOutcome:
        if retrieval_mode == "hybrid":
            retriever = HybridRetriever(self.settings)
            results = retriever.search(query, top_k=top_k, filters=filters)
            reasons = getattr(retriever, "last_degraded_reasons", [])
            return SearchOutcome(results=results, degraded=bool(reasons), degraded_reasons=list(reasons))
        if retrieval_mode == "bm25":
            candidates = BM25Index(self.settings).search(query, top_k=top_k, filters=filters)
            return SearchOutcome(
                results=self._candidates_to_results(candidates, mode="bm25"),
                degraded=False,
                degraded_reasons=[],
            )
        if retrieval_mode == "vector":
            candidates = ChromaVectorIndex(self.settings).search(query, top_k=top_k, filters=filters)
            return SearchOutcome(
                results=self._candidates_to_results(candidates, mode="vector"),
                degraded=False,
                degraded_reasons=[],
            )
        raise KnowledgeOpsError(
            ErrorCode.INVALID_REQUEST,
            "Unsupported retrieval mode.",
            {"retrieval_mode": retrieval_mode, "allowed": ["bm25", "vector", "hybrid"]},
        )

    def _candidates_to_results(
        self,
        candidates: list[RetrieverCandidate],
        *,
        mode: str,
    ) -> list[RetrievalResult]:
        results: list[RetrievalResult] = []
        for index, candidate in enumerate(candidates, start=1):
            record = self.corpus_by_id[candidate.chunk_id]
            citation = self.citation_builder.build(record, rank=index)
            vector_score = candidate.normalized_score if mode == "vector" else None
            bm25_score = candidate.normalized_score if mode == "bm25" else None
            results.append(
                RetrievalResult(
                    chunk_id=record.chunk.chunk_id,
                    doc_id=record.chunk.doc_id,
                    text=record.chunk.text,
                    metadata=record.chunk.metadata,
                    vector_score=vector_score,
                    bm25_score=bm25_score,
                    metadata_boost=0.0,
                    recency_boost=1.0,
                    hybrid_score=candidate.normalized_score,
                    rank=index,
                    citation=citation,
                )
            )
        return results

