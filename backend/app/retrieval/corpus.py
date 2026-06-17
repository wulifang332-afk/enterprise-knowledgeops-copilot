from __future__ import annotations

import json
from dataclasses import dataclass

from backend.app.core.settings import AppSettings
from backend.app.schemas.documents import Chunk


@dataclass(frozen=True)
class CorpusChunk:
    chunk: Chunk
    document_content: str


class ProcessedCorpus:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings

    def load(self) -> list[CorpusChunk]:
        chunks: list[CorpusChunk] = []
        for path in sorted(self.settings.processed_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            document_content = payload["content"]
            for raw_chunk in payload["chunks"]:
                chunks.append(
                    CorpusChunk(
                        chunk=Chunk.model_validate(raw_chunk),
                        document_content=document_content,
                    )
                )
        return chunks

    def by_chunk_id(self) -> dict[str, CorpusChunk]:
        return {record.chunk.chunk_id: record for record in self.load()}


def chunk_matches_filters(record: CorpusChunk, filters: dict | None) -> bool:
    if not filters:
        return True
    metadata = record.chunk.metadata
    checks = {
        "doc_ids": metadata.doc_id,
        "departments": metadata.department,
        "policy_types": metadata.policy_type.value,
        "owners": metadata.owner,
        "access_levels": metadata.access_level.value,
    }
    for key, actual in checks.items():
        expected_values = filters.get(key)
        if expected_values and actual not in expected_values:
            return False
    regions = filters.get("regions")
    if regions and not set(regions).intersection(set(metadata.regions)):
        return False
    section_titles = filters.get("section_titles")
    if section_titles and not any(value.casefold() in metadata.section_title.casefold() for value in section_titles):
        return False
    related_processes = filters.get("related_processes")
    if related_processes and not set(related_processes).intersection(set(metadata.related_processes)):
        return False
    return True
