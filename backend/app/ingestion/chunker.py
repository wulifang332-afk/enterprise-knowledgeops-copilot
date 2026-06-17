from __future__ import annotations

import re

from backend.app.core.settings import AppSettings
from backend.app.schemas.documents import Chunk, ChunkMetadata, DocumentMetadata, Section

from .utils import sha256_text, slugify

TOKEN_RE = re.compile(r"\S+")


class ChunkingService:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def chunk_document(self, *, metadata: DocumentMetadata, sections: list[Section]) -> list[Chunk]:
        chunks: list[Chunk] = []
        chunk_index = 1
        for section in sections:
            for local_index, span in enumerate(self._chunk_spans(section.text), start=1):
                relative_start, relative_end, token_count = span
                absolute_start = section.start_char + relative_start
                absolute_end = section.start_char + relative_end
                chunk_text = section.text[relative_start:relative_end]
                trimmed_text, absolute_start, absolute_end = self._trim_chunk_text(
                    chunk_text,
                    absolute_start,
                    absolute_end,
                )
                if not trimmed_text:
                    continue
                chunk_id = self._chunk_id(metadata.doc_id, section, local_index)
                related_process = metadata.related_processes[0] if metadata.related_processes else None
                chunk_metadata = ChunkMetadata(
                    **metadata.model_dump(),
                    chunk_id=chunk_id,
                    section_title=section.title,
                    section_path=section.section_path,
                    section_path_hash=section.section_path_hash,
                    heading_occurrence=section.heading_occurrence,
                    related_process=related_process,
                    chunk_index=chunk_index,
                )
                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        doc_id=metadata.doc_id,
                        text=trimmed_text,
                        metadata=chunk_metadata,
                        token_count=token_count,
                        start_char=absolute_start,
                        end_char=absolute_end,
                        text_sha256=sha256_text(trimmed_text),
                    )
                )
                chunk_index += 1
        return chunks

    def _chunk_spans(self, text: str) -> list[tuple[int, int, int]]:
        tokens = list(TOKEN_RE.finditer(text))
        if not tokens:
            return []
        if len(tokens) <= self.settings.chunk_max_tokens:
            return [(tokens[0].start(), tokens[-1].end(), len(tokens))]

        spans: list[tuple[int, int, int]] = []
        start_token = 0
        step = max(1, self.settings.chunk_target_tokens - self.settings.chunk_overlap_tokens)
        while start_token < len(tokens):
            end_token = min(start_token + self.settings.chunk_target_tokens, len(tokens))
            span_tokens = tokens[start_token:end_token]
            spans.append((span_tokens[0].start(), span_tokens[-1].end(), len(span_tokens)))
            if end_token == len(tokens):
                break
            start_token += step
        return spans

    @staticmethod
    def _trim_chunk_text(text: str, absolute_start: int, absolute_end: int) -> tuple[str, int, int]:
        leading = len(text) - len(text.lstrip())
        trailing = len(text.rstrip())
        trimmed = text.strip()
        return trimmed, absolute_start + leading, absolute_start + trailing

    @staticmethod
    def _chunk_id(doc_id: str, section: Section, local_index: int) -> str:
        section_slug = slugify(section.title)
        return (
            f"chk:{doc_id}:{section_slug}:"
            f"{section.heading_occurrence:02d}:{section.section_path_hash}:{local_index:03d}"
        )

