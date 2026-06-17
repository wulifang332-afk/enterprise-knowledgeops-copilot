from __future__ import annotations

import hashlib
import math
import re

import numpy as np

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", re.IGNORECASE)


class MockEmbeddingProvider:
    """Deterministic local embedding provider for API-key-free retrieval tests."""

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_text(text)

    def embed_text(self, text: str) -> list[float]:
        vector = np.zeros(self.dimensions, dtype=np.float32)
        features = self._features(text)
        if not features:
            return vector.tolist()
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = math.sqrt(float(np.dot(vector, vector)))
        if norm == 0:
            return vector.tolist()
        return (vector / norm).astype(float).tolist()

    @staticmethod
    def _features(text: str) -> list[str]:
        normalized = text.lower()
        tokens = TOKEN_RE.findall(normalized)
        features = [f"tok:{token}" for token in tokens]
        features.extend(f"bi:{tokens[index]}_{tokens[index + 1]}" for index in range(len(tokens) - 1))
        compact = re.sub(r"\s+", " ", normalized)
        features.extend(f"tri:{compact[index:index + 3]}" for index in range(max(0, len(compact) - 2)))
        return features

