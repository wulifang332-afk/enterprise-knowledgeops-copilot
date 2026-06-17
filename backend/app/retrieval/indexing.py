from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.settings import AppSettings

from .bm25 import BM25Index
from .corpus import ProcessedCorpus
from .vector import ChromaVectorIndex


@dataclass(frozen=True)
class IndexRebuildResult:
    chunk_count: int
    bm25_index: str
    chroma_index: str


class IndexRebuildService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def rebuild_all(self) -> IndexRebuildResult:
        chunks = ProcessedCorpus(self.settings).load()
        BM25Index(self.settings).build(chunks)
        ChromaVectorIndex(self.settings).build(chunks)
        return IndexRebuildResult(
            chunk_count=len(chunks),
            bm25_index=str(self.settings.bm25_index_dir / "index.json"),
            chroma_index=str(self.settings.chroma_index_dir),
        )

