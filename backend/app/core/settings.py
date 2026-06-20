from __future__ import annotations

import os
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


def default_project_root() -> Path:
    return Path(__file__).resolve().parents[3]


class AppSettings(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_root: Path = Field(default_factory=default_project_root)
    data_dir: Path | None = None
    allowed_file_types: tuple[str, ...] = (".md", ".txt")
    max_file_bytes: int = 2 * 1024 * 1024
    chunk_target_tokens: int = 600
    chunk_max_tokens: int = 800
    chunk_overlap_tokens: int = 100
    retrieval_top_k_default: int = 5
    retrieval_top_k_max: int = 20
    mock_embedding_dimensions: int = 384

    @model_validator(mode="after")
    def derive_paths(self) -> "AppSettings":
        if self.data_dir is None:
            env_value = os.getenv("DATA_DIR", "data")
            data_path = Path(env_value)
            self.data_dir = data_path if data_path.is_absolute() else self.project_root / data_path
        return self

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def audit_dir(self) -> Path:
        return self.data_dir / "audit"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "knowledgeops.db"

    @property
    def indexes_dir(self) -> Path:
        return self.data_dir / "indexes"

    @property
    def bm25_index_dir(self) -> Path:
        return self.indexes_dir / "bm25"

    @property
    def chroma_index_dir(self) -> Path:
        return self.indexes_dir / "chroma"

    @property
    def graph_dir(self) -> Path:
        return self.data_dir / "graph"

    @property
    def evaluation_dir(self) -> Path:
        return self.data_dir / "evaluation"

    @property
    def feedback_dir(self) -> Path:
        return self.data_dir / "feedback"

    def ensure_data_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.raw_dir,
            self.processed_dir,
            self.audit_dir,
            self.indexes_dir,
            self.graph_dir,
            self.evaluation_dir,
            self.feedback_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
