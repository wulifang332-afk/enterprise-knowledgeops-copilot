from __future__ import annotations

from typing import Any

import yaml
from pydantic import ValidationError

from backend.app.core.errors import KnowledgeOpsError
from backend.app.schemas.documents import DocumentMetadata
from backend.app.schemas.enums import ErrorCode

from .utils import sha256_text


GENERATED_METADATA_FIELDS = {"source_file", "content_sha256"}


class ParsedDocumentText:
    def __init__(self, metadata: DocumentMetadata, content: str) -> None:
        self.metadata = metadata
        self.content = content


class MetadataParser:
    def parse(self, *, normalized_text: str, source_file: str) -> ParsedDocumentText:
        front_matter, body = self._split_front_matter(normalized_text)
        raw_metadata = self._load_yaml(front_matter)
        for field_name in GENERATED_METADATA_FIELDS:
            raw_metadata.pop(field_name, None)

        if not body.strip():
            raise KnowledgeOpsError(
                ErrorCode.EMPTY_DOCUMENT,
                "Document body is empty after front matter removal.",
                {"source_file": source_file},
            )

        raw_metadata["source_file"] = source_file
        raw_metadata["content_sha256"] = sha256_text(body)

        try:
            metadata = DocumentMetadata.model_validate(raw_metadata)
        except ValidationError as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_METADATA,
                "Document metadata failed validation.",
                {"source_file": source_file, "errors": exc.errors()},
            ) from exc

        return ParsedDocumentText(metadata=metadata, content=body)

    @staticmethod
    def _split_front_matter(normalized_text: str) -> tuple[str, str]:
        if not normalized_text.startswith("---\n"):
            raise KnowledgeOpsError(
                ErrorCode.INVALID_METADATA,
                "Document must start with YAML front matter.",
            )
        end_marker = normalized_text.find("\n---\n", 4)
        if end_marker == -1:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_METADATA,
                "Document YAML front matter must close with ---.",
            )
        front_matter = normalized_text[4:end_marker]
        body = normalized_text[end_marker + len("\n---\n") :]
        return front_matter, body

    @staticmethod
    def _load_yaml(front_matter: str) -> dict[str, Any]:
        try:
            loaded = yaml.safe_load(front_matter)
        except yaml.YAMLError as exc:
            raise KnowledgeOpsError(
                ErrorCode.INVALID_METADATA,
                "Document YAML front matter is invalid.",
            ) from exc
        if not isinstance(loaded, dict):
            raise KnowledgeOpsError(
                ErrorCode.INVALID_METADATA,
                "Document YAML front matter must be an object.",
            )
        return loaded

