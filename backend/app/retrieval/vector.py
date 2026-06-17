from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import chromadb

from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.schemas.enums import ErrorCode

from .corpus import CorpusChunk, ProcessedCorpus, chunk_matches_filters
from .embeddings import MockEmbeddingProvider
from .types import RetrieverCandidate

COLLECTION_NAME = "knowledgeops_chunks"


class ChromaVectorIndex:
    def __init__(
        self,
        settings: AppSettings,
        embedding_provider: MockEmbeddingProvider | None = None,
    ) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider or MockEmbeddingProvider(
            dimensions=settings.mock_embedding_dimensions
        )
        self.index_dir = settings.chroma_index_dir
        self.manifest_path = settings.indexes_dir / "chroma_manifest.json"
        self._corpus_by_id: dict[str, CorpusChunk] | None = None

    def build(self, chunks: list[CorpusChunk] | None = None) -> None:
        chunks = chunks or ProcessedCorpus(self.settings).load()
        if not chunks:
            raise KnowledgeOpsError(
                ErrorCode.INDEX_UNAVAILABLE,
                "Cannot build vector index because no processed chunks are available.",
            )
        tmp_dir = self.settings.indexes_dir / f".tmp_chroma_{uuid4().hex}"
        backup_dir = self.settings.indexes_dir / ".backup_chroma"
        try:
            self._build_into(tmp_dir, chunks)
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            if self.index_dir.exists():
                self.index_dir.rename(backup_dir)
            tmp_dir.rename(self.index_dir)
            if backup_dir.exists():
                shutil.rmtree(backup_dir)
            self._write_manifest(chunks)
        except Exception as exc:
            if not self.index_dir.exists() and backup_dir.exists():
                backup_dir.rename(self.index_dir)
            if tmp_dir.exists():
                shutil.rmtree(tmp_dir)
            if isinstance(exc, KnowledgeOpsError):
                raise
            raise KnowledgeOpsError(
                ErrorCode.INDEX_UNAVAILABLE,
                "Vector index rebuild failed; previous valid index was preserved.",
                {"reason": str(exc)},
            ) from exc

    def search(self, query: str, *, top_k: int = 5, filters: dict | None = None) -> list[RetrieverCandidate]:
        if not self.index_dir.exists():
            raise KnowledgeOpsError(ErrorCode.INDEX_UNAVAILABLE, "Vector index is unavailable.")
        try:
            client = chromadb.PersistentClient(path=str(self.index_dir))
            collection = client.get_collection(COLLECTION_NAME)
            result = collection.query(
                query_embeddings=[self.embedding_provider.embed_query(query)],
                n_results=max(top_k * 4, top_k),
                include=["distances"],
            )
        except Exception as exc:
            raise KnowledgeOpsError(ErrorCode.INDEX_UNAVAILABLE, "Vector index cannot be queried.") from exc
        corpus_by_id = self._load_corpus_by_id()
        candidates: list[RetrieverCandidate] = []
        ids = result.get("ids", [[]])[0]
        distances = result.get("distances", [[]])[0]
        for chunk_id, distance in zip(ids, distances, strict=False):
            record = corpus_by_id.get(chunk_id)
            if record is None or not chunk_matches_filters(record, filters):
                continue
            score = max(0.0, min(1.0, 1.0 - float(distance)))
            candidates.append(
                RetrieverCandidate(
                    chunk_id=chunk_id,
                    raw_score=score,
                    normalized_score=score,
                    rank=len(candidates) + 1,
                )
            )
            if len(candidates) >= top_k:
                break
        return candidates

    def _build_into(self, path: Path, chunks: list[CorpusChunk]) -> None:
        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))
        collection = client.get_or_create_collection(
            COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        collection.add(
            ids=[record.chunk.chunk_id for record in chunks],
            documents=[record.chunk.text for record in chunks],
            embeddings=self.embedding_provider.embed_documents([record.chunk.text for record in chunks]),
            metadatas=[self._metadata_for_chroma(record) for record in chunks],
        )

    def _write_manifest(self, chunks: list[CorpusChunk]) -> None:
        payload = {
            "schema_version": 1,
            "backend": "chroma",
            "collection": COLLECTION_NAME,
            "embedding_provider": "mock",
            "embedding_dimensions": self.embedding_provider.dimensions,
            "chunk_count": len(chunks),
            "chunk_hashes": {
                record.chunk.chunk_id: record.chunk.text_sha256
                for record in chunks
            },
        }
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(payload, ensure_ascii=True, sort_keys=True), encoding="utf-8")

    def _load_corpus_by_id(self) -> dict[str, CorpusChunk]:
        if self._corpus_by_id is None:
            self._corpus_by_id = ProcessedCorpus(self.settings).by_chunk_id()
        return self._corpus_by_id

    @staticmethod
    def _metadata_for_chroma(record: CorpusChunk) -> dict[str, str]:
        metadata = record.chunk.metadata
        return {
            "doc_id": metadata.doc_id,
            "chunk_id": metadata.chunk_id,
            "title": metadata.title,
            "section_title": metadata.section_title,
            "department": metadata.department,
            "regions": "|".join(metadata.regions),
            "policy_type": metadata.policy_type.value,
            "access_level": metadata.access_level.value,
            "source_file": metadata.source_file,
        }

