from __future__ import annotations

from backend.app.citations.builder import CitationBuilder
from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.retrieval import RetrievalResult

from .bm25 import BM25Index
from .corpus import CorpusChunk, ProcessedCorpus
from .reranker import BaseReranker, NoOpReranker
from .types import RetrieverCandidate
from .vector import ChromaVectorIndex


class HybridRetriever:
    def __init__(
        self,
        settings: AppSettings,
        bm25_index: BM25Index | None = None,
        vector_index: ChromaVectorIndex | None = None,
        citation_builder: CitationBuilder | None = None,
        reranker: BaseReranker | None = None,
    ) -> None:
        self.settings = settings
        self.bm25_index = bm25_index or BM25Index(settings)
        self.vector_index = vector_index or ChromaVectorIndex(settings)
        self.citation_builder = citation_builder or CitationBuilder()
        self.reranker = reranker or NoOpReranker()
        self.corpus_by_id = ProcessedCorpus(settings).by_chunk_id()
        self.last_degraded_reasons: list[str] = []

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        filters: dict | None = None,
        minimum_score: float = 0.0,
    ) -> list[RetrievalResult]:
        top_k = self._validate_top_k(top_k)
        self.last_degraded_reasons = []
        candidate_pool_size = min(top_k * 4, 80)
        bm25_candidates, bm25_error = self._safe_bm25(query, top_k=candidate_pool_size, filters=filters)
        vector_candidates, vector_error = self._safe_vector(query, top_k=candidate_pool_size, filters=filters)
        if bm25_error and vector_error:
            raise KnowledgeOpsError(
                ErrorCode.INDEX_UNAVAILABLE,
                "Both BM25 and vector indexes are unavailable.",
                {"bm25": bm25_error.message, "vector": vector_error.message},
            )
        if bm25_error:
            self.last_degraded_reasons.append(bm25_error.message)
        if vector_error:
            self.last_degraded_reasons.append(vector_error.message)

        weights = self._weights(bm25_available=not bm25_error, vector_available=not vector_error)
        scored = self._score_candidates(
            bm25_candidates=bm25_candidates,
            vector_candidates=vector_candidates,
            filters=filters,
            weights=weights,
        )
        scored = [item for item in scored if item[1]["hybrid_score"] >= minimum_score]
        scored.sort(key=lambda item: (-item[1]["hybrid_score"], item[0]))
        results = [
            self._to_result(chunk_id, scores, rank=index + 1)
            for index, (chunk_id, scores) in enumerate(scored[:top_k])
        ]
        return self.reranker.rerank(query, results)

    def _score_candidates(
        self,
        *,
        bm25_candidates: list[RetrieverCandidate],
        vector_candidates: list[RetrieverCandidate],
        filters: dict | None,
        weights: dict[str, float],
    ) -> list[tuple[str, dict[str, float | None]]]:
        candidate_ids = {candidate.chunk_id for candidate in bm25_candidates}
        candidate_ids.update(candidate.chunk_id for candidate in vector_candidates)
        bm25_scores = {candidate.chunk_id: candidate.normalized_score for candidate in bm25_candidates}
        vector_scores = {candidate.chunk_id: candidate.normalized_score for candidate in vector_candidates}
        scored: list[tuple[str, dict[str, float | None]]] = []
        for chunk_id in candidate_ids:
            record = self.corpus_by_id.get(chunk_id)
            if record is None:
                continue
            metadata_boost = self._metadata_boost(record, filters)
            recency_boost = 1.0
            vector_score = vector_scores.get(chunk_id)
            bm25_score = bm25_scores.get(chunk_id)
            hybrid_score = (
                weights["vector"] * (vector_score or 0.0)
                + weights["bm25"] * (bm25_score or 0.0)
                + weights["metadata"] * metadata_boost
                + weights["recency"] * recency_boost
            )
            scored.append(
                (
                    chunk_id,
                    {
                        "vector_score": vector_score,
                        "bm25_score": bm25_score,
                        "metadata_boost": metadata_boost,
                        "recency_boost": recency_boost,
                        "hybrid_score": max(0.0, min(1.0, hybrid_score)),
                    },
                )
            )
        return scored

    def _to_result(self, chunk_id: str, scores: dict[str, float | None], *, rank: int) -> RetrievalResult:
        record = self.corpus_by_id[chunk_id]
        citation = self.citation_builder.build(record, rank=rank)
        return RetrievalResult(
            chunk_id=record.chunk.chunk_id,
            doc_id=record.chunk.doc_id,
            text=record.chunk.text,
            metadata=record.chunk.metadata,
            vector_score=scores["vector_score"],
            bm25_score=scores["bm25_score"],
            metadata_boost=float(scores["metadata_boost"] or 0.0),
            recency_boost=float(scores["recency_boost"] or 0.0),
            hybrid_score=float(scores["hybrid_score"] or 0.0),
            rank=rank,
            citation=citation,
        )

    def _safe_bm25(
        self,
        query: str,
        *,
        top_k: int,
        filters: dict | None,
    ) -> tuple[list[RetrieverCandidate], KnowledgeOpsError | None]:
        try:
            return self.bm25_index.search(query, top_k=top_k, filters=filters), None
        except KnowledgeOpsError as exc:
            if exc.error_code == ErrorCode.INDEX_UNAVAILABLE:
                return [], exc
            raise

    def _safe_vector(
        self,
        query: str,
        *,
        top_k: int,
        filters: dict | None,
    ) -> tuple[list[RetrieverCandidate], KnowledgeOpsError | None]:
        try:
            return self.vector_index.search(query, top_k=top_k, filters=filters), None
        except KnowledgeOpsError as exc:
            if exc.error_code == ErrorCode.INDEX_UNAVAILABLE:
                return [], exc
            raise

    def _validate_top_k(self, top_k: int) -> int:
        if top_k < 1:
            return 1
        return min(top_k, self.settings.retrieval_top_k_max)

    @staticmethod
    def _weights(*, bm25_available: bool, vector_available: bool) -> dict[str, float]:
        if bm25_available and vector_available:
            return {"vector": 0.55, "bm25": 0.35, "metadata": 0.05, "recency": 0.05}
        if bm25_available:
            return {"vector": 0.0, "bm25": 0.90, "metadata": 0.05, "recency": 0.05}
        return {"vector": 0.90, "bm25": 0.0, "metadata": 0.05, "recency": 0.05}

    @staticmethod
    def _metadata_boost(record: CorpusChunk, filters: dict | None) -> float:
        if not filters:
            return 0.0
        checks = 0
        matches = 0
        metadata = record.chunk.metadata
        scalar_fields = {
            "doc_ids": metadata.doc_id,
            "departments": metadata.department,
            "policy_types": metadata.policy_type.value,
            "owners": metadata.owner,
            "access_levels": metadata.access_level.value,
        }
        for key, actual in scalar_fields.items():
            expected = filters.get(key)
            if expected:
                checks += 1
                matches += int(actual in expected)
        regions = filters.get("regions")
        if regions:
            checks += 1
            matches += int(bool(set(regions).intersection(set(metadata.regions))))
        section_titles = filters.get("section_titles")
        if section_titles:
            checks += 1
            matches += int(any(value.casefold() in metadata.section_title.casefold() for value in section_titles))
        related_processes = filters.get("related_processes")
        if related_processes:
            checks += 1
            matches += int(bool(set(related_processes).intersection(set(metadata.related_processes))))
        return matches / checks if checks else 0.0
