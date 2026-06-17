from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend.app.core.settings import AppSettings
from backend.app.ingestion.service import IngestionService
from backend.app.schemas.enums import ErrorCode, IngestionStatus

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_RAW_DIR = PROJECT_ROOT / "data" / "raw"


def make_settings(tmp_path: Path, *, max_file_bytes: int | None = None) -> AppSettings:
    data_dir = tmp_path / "data"
    (data_dir / "raw").mkdir(parents=True, exist_ok=True)
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    if max_file_bytes is not None:
        settings.max_file_bytes = max_file_bytes
    return settings


def copy_sample_docs(raw_dir: Path) -> None:
    for source in SAMPLE_RAW_DIR.glob("*.md"):
        shutil.copy2(source, raw_dir / source.name)


def load_processed(settings: AppSettings, doc_id: str) -> dict:
    with (settings.processed_dir / f"{doc_id}.json").open(encoding="utf-8") as handle:
        return json.load(handle)


def valid_doc_text(doc_id: str = "test-policy-v1-0", title: str = "Test Policy") -> str:
    return f"""---
doc_id: {doc_id}
title: {title}
department: Test Department
regions:
  - Global
policy_type: policy
effective_date: "2025-01-01"
version: "1.0"
access_level: internal
owner: Test Owner
related_processes:
  - Test Process
created_at: "2025-01-01T00:00:00Z"
updated_at: "2025-01-01T00:00:00Z"
---
# {title}

## Overview

This policy contains valid synthetic test content for ingestion.
"""


def test_all_sample_documents_ingest_and_write_processed_json(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    copy_sample_docs(settings.raw_dir)

    summary = IngestionService(settings=settings).ingest_all_raw(request_id="test-ingest-all")

    assert summary.total_files == 8
    assert summary.ingested_count == 8
    assert summary.failed_count == 0
    assert summary.skipped_count == 0

    service = IngestionService(settings=settings)
    assert service.repository.count_documents() == 8
    assert service.repository.count_chunks() == 40

    processed_files = sorted(settings.processed_dir.glob("*.json"))
    assert len(processed_files) == 8

    required_metadata_fields = {
        "doc_id",
        "title",
        "department",
        "regions",
        "policy_type",
        "effective_date",
        "version",
        "access_level",
        "owner",
        "source_file",
        "related_processes",
        "created_at",
        "updated_at",
        "content_sha256",
    }
    for processed_file in processed_files:
        payload = json.loads(processed_file.read_text(encoding="utf-8"))
        metadata = payload["metadata"]
        assert required_metadata_fields.issubset(metadata)
        assert all(metadata[field] not in (None, "", []) for field in required_metadata_fields)
        assert metadata["source_file"].startswith("data/raw/")
        assert len(metadata["content_sha256"]) == 64
        assert payload["sections"]
        assert payload["chunks"]


def test_reingestion_is_idempotent_and_chunk_ids_are_stable(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    copy_sample_docs(settings.raw_dir)
    service = IngestionService(settings=settings)

    first = service.ingest_all_raw(request_id="first")
    first_ids = {
        result.doc_id: [
            chunk["chunk_id"]
            for chunk in load_processed(settings, result.doc_id)["chunks"]
        ]
        for result in first.results
        if result.doc_id
    }

    second = service.ingest_all_raw(request_id="second")
    second_ids = {
        doc_id: [
            chunk["chunk_id"]
            for chunk in load_processed(settings, doc_id)["chunks"]
        ]
        for doc_id in first_ids
    }

    assert first.ingested_count == 8
    assert second.skipped_count == 8
    assert second.failed_count == 0
    assert first_ids == second_ids
    assert service.repository.count_documents() == 8
    assert service.repository.count_chunks() == 40


def test_stable_chunks_across_clean_runs(tmp_path: Path) -> None:
    settings_a = make_settings(tmp_path / "run-a")
    settings_b = make_settings(tmp_path / "run-b")
    copy_sample_docs(settings_a.raw_dir)
    copy_sample_docs(settings_b.raw_dir)

    IngestionService(settings=settings_a).ingest_all_raw(request_id="run-a")
    IngestionService(settings=settings_b).ingest_all_raw(request_id="run-b")

    chunks_a = {
        file.name: [
            (chunk["chunk_id"], chunk["text_sha256"])
            for chunk in json.loads(file.read_text(encoding="utf-8"))["chunks"]
        ]
        for file in sorted(settings_a.processed_dir.glob("*.json"))
    }
    chunks_b = {
        file.name: [
            (chunk["chunk_id"], chunk["text_sha256"])
            for chunk in json.loads(file.read_text(encoding="utf-8"))["chunks"]
        ]
        for file in sorted(settings_b.processed_dir.glob("*.json"))
    }

    assert chunks_a == chunks_b


def test_invalid_metadata_returns_invalid_metadata(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.raw_dir / "invalid.md").write_text(
        """---
doc_id: invalid-policy-v1-0
department: Test Department
regions:
  - Global
policy_type: policy
effective_date: "2025-01-01"
version: "1.0"
access_level: internal
owner: Test Owner
created_at: "2025-01-01T00:00:00Z"
updated_at: "2025-01-01T00:00:00Z"
---
# Missing Title

This document is missing the required title metadata field.
""",
        encoding="utf-8",
    )

    summary = IngestionService(settings=settings).ingest_paths(["invalid.md"], request_id="invalid")

    assert summary.failed_count == 1
    assert summary.results[0].status == IngestionStatus.FAILED
    assert summary.results[0].error_code == ErrorCode.INVALID_METADATA


def test_generated_metadata_fields_are_not_trusted_from_yaml(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.raw_dir / "generated-fields.md").write_text(
        valid_doc_text().replace(
            "updated_at: \"2025-01-01T00:00:00Z\"",
            "updated_at: \"2025-01-01T00:00:00Z\"\nsource_file: /tmp/not-real.md\ncontent_sha256: bad",
        ),
        encoding="utf-8",
    )

    summary = IngestionService(settings=settings).ingest_paths(
        ["generated-fields.md"],
        request_id="generated-fields",
    )

    assert summary.ingested_count == 1
    payload = load_processed(settings, "test-policy-v1-0")
    assert payload["metadata"]["source_file"] == "data/raw/generated-fields.md"
    assert payload["metadata"]["content_sha256"] != "bad"
    assert len(payload["metadata"]["content_sha256"]) == 64


def test_path_validation_rejects_unsafe_inputs(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, max_file_bytes=20)
    (settings.raw_dir / "unsupported.pdf").write_text("not a supported file", encoding="utf-8")
    (settings.raw_dir / "oversized.md").write_text(valid_doc_text(), encoding="utf-8")
    outside = tmp_path / "outside.md"
    outside.write_text(valid_doc_text("outside-policy-v1-0", "Outside Policy"), encoding="utf-8")

    service = IngestionService(settings=settings)
    absolute_result = service.ingest_paths([str(outside)], request_id="absolute").results[0]
    traversal_result = service.ingest_paths(["../outside.md"], request_id="traversal").results[0]
    unsupported_result = service.ingest_paths(["unsupported.pdf"], request_id="unsupported").results[0]
    oversized_result = service.ingest_paths(["oversized.md"], request_id="oversized").results[0]

    assert absolute_result.error_code == ErrorCode.INVALID_FILE_PATH
    assert traversal_result.error_code == ErrorCode.INVALID_FILE_PATH
    assert unsupported_result.error_code == ErrorCode.UNSUPPORTED_FILE_TYPE
    assert oversized_result.error_code == ErrorCode.INVALID_FILE_PATH


def test_symlink_escape_is_rejected(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    outside = tmp_path / "outside.md"
    outside.write_text(valid_doc_text("outside-policy-v1-0", "Outside Policy"), encoding="utf-8")
    symlink = settings.raw_dir / "link.md"
    try:
        symlink.symlink_to(outside)
    except OSError:
        pytest.skip("Symlink creation is not available in this environment.")

    result = IngestionService(settings=settings).ingest_paths(["link.md"], request_id="symlink").results[0]

    assert result.status == IngestionStatus.FAILED
    assert result.error_code == ErrorCode.INVALID_FILE_PATH


def test_duplicate_section_slugs_produce_unique_chunk_ids(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    (settings.raw_dir / "duplicate-sections.md").write_text(
        valid_doc_text("duplicate-sections-v1-0", "Duplicate Sections Policy")
        + "\n## Details\n\nFirst details section.\n\n## Details\n\nSecond details section.\n",
        encoding="utf-8",
    )

    summary = IngestionService(settings=settings).ingest_paths(
        ["duplicate-sections.md"],
        request_id="duplicate-sections",
    )

    assert summary.ingested_count == 1
    payload = load_processed(settings, "duplicate-sections-v1-0")
    chunk_ids = [chunk["chunk_id"] for chunk in payload["chunks"]]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert any(":details:01:" in chunk_id for chunk_id in chunk_ids)
    assert any(":details:02:" in chunk_id for chunk_id in chunk_ids)

