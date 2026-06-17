from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrieverCandidate:
    chunk_id: str
    raw_score: float
    normalized_score: float
    rank: int

