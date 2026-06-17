from __future__ import annotations

import hashlib

from backend.app.core.errors import KnowledgeOpsError
from backend.app.schemas.enums import ErrorCode
from backend.app.schemas.retrieval import Citation

from backend.app.retrieval.corpus import CorpusChunk


def normalize_quote_for_hash(quote: str) -> str:
    return quote.replace("\r\n", "\n").replace("\r", "\n").strip()


def quote_hash(quote: str) -> str:
    return hashlib.sha256(normalize_quote_for_hash(quote).encode("utf-8")).hexdigest()


class CitationBuilder:
    def build(self, record: CorpusChunk, *, rank: int) -> Citation:
        chunk = record.chunk
        quote = chunk.text
        expected = record.document_content[chunk.start_char : chunk.end_char]
        if expected != quote:
            raise KnowledgeOpsError(
                ErrorCode.CITATION_VALIDATION_FAILED,
                "Citation quote and offsets do not match source document content.",
                {
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                },
            )
        metadata = chunk.metadata
        return Citation(
            citation_id=f"CIT-{rank}",
            doc_id=chunk.doc_id,
            chunk_id=chunk.chunk_id,
            title=metadata.title,
            section_title=metadata.section_title,
            source_file=metadata.source_file,
            version=metadata.version,
            effective_date=metadata.effective_date,
            quote=quote,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            quote_hash=quote_hash(quote),
        )

