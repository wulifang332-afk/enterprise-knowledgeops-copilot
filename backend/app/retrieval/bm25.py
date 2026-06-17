from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode

from .corpus import CorpusChunk, ProcessedCorpus, chunk_matches_filters
from .types import RetrieverCandidate

TOKEN_RE = re.compile(
    r"[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)*|\d+(?:,\d{3})*(?:\.\d+)?|\$|€|£"
)


def tokenize_for_bm25(text: str) -> list[str]:
    base_tokens = [token.lower() for token in TOKEN_RE.findall(text)]
    expanded: list[str] = []
    for token in base_tokens:
        expanded.append(token)
        if any(char.isdigit() for char in token):
            expanded.append(token.replace(",", ""))
        if "-" in token or "_" in token:
            parts = re.split(r"[-_]+", token)
            expanded.extend(part for part in parts if part)
            expanded.append("".join(parts))
    expanded.extend(
        f"{expanded[index]}__{expanded[index + 1]}"
        for index in range(len(expanded) - 1)
    )
    expanded.extend(
        f"{expanded[index]}__{expanded[index + 1]}__{expanded[index + 2]}"
        for index in range(len(expanded) - 2)
    )
    return expanded


class BM25Index:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.index_path = settings.bm25_index_dir / "index.json"
        self._index: dict[str, Any] | None = None
        self._corpus_by_id: dict[str, CorpusChunk] | None = None

    def build(self, chunks: list[CorpusChunk] | None = None) -> None:
        chunks = chunks or ProcessedCorpus(self.settings).load()
        if not chunks:
            raise KnowledgeOpsError(
                ErrorCode.INDEX_UNAVAILABLE,
                "Cannot build BM25 index because no processed chunks are available.",
            )
        documents: list[dict[str, Any]] = []
        document_frequency: dict[str, int] = defaultdict(int)
        for record in chunks:
            tokens = tokenize_for_bm25(self._indexable_text(record))
            counts = Counter(tokens)
            documents.append(
                {
                    "chunk_id": record.chunk.chunk_id,
                    "tokens": dict(counts),
                    "length": len(tokens),
                }
            )
            for token in counts:
                document_frequency[token] += 1
        doc_count = len(documents)
        avgdl = sum(document["length"] for document in documents) / doc_count
        idf = {
            token: math.log(1 + (doc_count - freq + 0.5) / (freq + 0.5))
            for token, freq in document_frequency.items()
        }
        payload = {
            "schema_version": 1,
            "doc_count": doc_count,
            "avgdl": avgdl,
            "k1": 1.5,
            "b": 0.75,
            "idf": idf,
            "documents": documents,
        }
        self._atomic_write(payload)
        self._index = payload
        self._corpus_by_id = {record.chunk.chunk_id: record for record in chunks}

    def search(self, query: str, *, top_k: int = 5, filters: dict | None = None) -> list[RetrieverCandidate]:
        index = self._load_index()
        corpus_by_id = self._load_corpus_by_id()
        query_tokens = tokenize_for_bm25(query)
        if not query_tokens:
            return []
        query_counts = Counter(query_tokens)
        scored: list[tuple[str, float]] = []
        for document in index["documents"]:
            chunk_id = document["chunk_id"]
            record = corpus_by_id.get(chunk_id)
            if record is None or not chunk_matches_filters(record, filters):
                continue
            score = self._score_document(document, query_counts, index)
            scored.append((chunk_id, score))
        scored.sort(key=lambda item: (-item[1], item[0]))
        normalized = self.normalize_scores([score for _, score in scored])
        return [
            RetrieverCandidate(
                chunk_id=chunk_id,
                raw_score=score,
                normalized_score=normalized[index],
                rank=index + 1,
            )
            for index, (chunk_id, score) in enumerate(scored[:top_k])
        ]

    @staticmethod
    def normalize_scores(scores: list[float]) -> list[float]:
        if not scores:
            return []
        max_score = max(scores)
        min_score = min(scores)
        if max_score == min_score:
            return [1.0 if max_score > 0 else 0.0 for _ in scores]
        return [(score - min_score) / (max_score - min_score) for score in scores]

    def _score_document(
        self,
        document: dict[str, Any],
        query_counts: Counter[str],
        index: dict[str, Any],
    ) -> float:
        score = 0.0
        doc_length = document["length"] or 1
        avgdl = index["avgdl"] or 1
        k1 = index["k1"]
        b = index["b"]
        token_counts = document["tokens"]
        for token, query_count in query_counts.items():
            frequency = token_counts.get(token, 0)
            if frequency == 0:
                continue
            denominator = frequency + k1 * (1 - b + b * doc_length / avgdl)
            score += index["idf"].get(token, 0.0) * (frequency * (k1 + 1) / denominator) * query_count
        return score

    def _load_index(self) -> dict[str, Any]:
        if self._index is not None:
            return self._index
        if not self.index_path.exists():
            raise KnowledgeOpsError(ErrorCode.INDEX_UNAVAILABLE, "BM25 index is unavailable.")
        try:
            self._index = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise KnowledgeOpsError(ErrorCode.INDEX_UNAVAILABLE, "BM25 index cannot be loaded.") from exc
        return self._index

    def _load_corpus_by_id(self) -> dict[str, CorpusChunk]:
        if self._corpus_by_id is None:
            self._corpus_by_id = ProcessedCorpus(self.settings).by_chunk_id()
        return self._corpus_by_id

    def _atomic_write(self, payload: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.index_path.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")
        tmp_path.replace(self.index_path)

    @staticmethod
    def _indexable_text(record: CorpusChunk) -> str:
        metadata = record.chunk.metadata
        return "\n".join(
            [
                metadata.title,
                metadata.section_title,
                metadata.department,
                " ".join(metadata.regions),
                metadata.owner,
                " ".join(metadata.related_processes),
                record.chunk.text,
            ]
        )

