from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.app.core.settings import AppSettings
from backend.app.schemas.documents import Chunk, Document, Section


class SQLiteRepository:
    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.settings.ensure_data_dirs()
        self.db_path = self.settings.db_path
        self.initialize()

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    department TEXT NOT NULL,
                    access_level TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    content TEXT NOT NULL,
                    ingested_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sections (
                    section_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    section_json TEXT NOT NULL,
                    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    doc_id TEXT NOT NULL,
                    section_title TEXT NOT NULL,
                    text_sha256 TEXT NOT NULL,
                    chunk_json TEXT NOT NULL,
                    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
                )
                """
            )
            connection.commit()

    def get_document_content_hash(self, doc_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT content_sha256 FROM documents WHERE doc_id = ?",
                (doc_id,),
            ).fetchone()
        return row["content_sha256"] if row else None

    def upsert_document(self, document: Document) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO documents (
                    doc_id, title, department, access_level, source_file,
                    content_sha256, metadata_json, content, ingested_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(doc_id) DO UPDATE SET
                    title = excluded.title,
                    department = excluded.department,
                    access_level = excluded.access_level,
                    source_file = excluded.source_file,
                    content_sha256 = excluded.content_sha256,
                    metadata_json = excluded.metadata_json,
                    content = excluded.content,
                    ingested_at = excluded.ingested_at
                """,
                (
                    document.metadata.doc_id,
                    document.metadata.title,
                    document.metadata.department,
                    document.metadata.access_level.value,
                    document.metadata.source_file,
                    document.metadata.content_sha256,
                    json.dumps(document.metadata.model_dump(mode="json"), sort_keys=True),
                    document.content,
                    document.ingested_at.isoformat(),
                ),
            )
            connection.execute("DELETE FROM sections WHERE doc_id = ?", (document.metadata.doc_id,))
            connection.execute("DELETE FROM chunks WHERE doc_id = ?", (document.metadata.doc_id,))
            for section in document.sections:
                self._insert_section(connection, section)
            for chunk in document.chunks:
                self._insert_chunk(connection, chunk)
            connection.commit()

    def count_documents(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM documents").fetchone()
        return int(row["count"])

    def count_chunks(self) -> int:
        with self._connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM chunks").fetchone()
        return int(row["count"])

    def fetch_chunks_for_document(self, doc_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT chunk_json FROM chunks WHERE doc_id = ? ORDER BY chunk_id",
                (doc_id,),
            ).fetchall()
        return [json.loads(row["chunk_json"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _insert_section(connection: sqlite3.Connection, section: Section) -> None:
        connection.execute(
            """
            INSERT INTO sections (section_id, doc_id, section_json)
            VALUES (?, ?, ?)
            """,
            (
                section.section_id,
                section.doc_id,
                json.dumps(section.model_dump(mode="json"), sort_keys=True),
            ),
        )

    @staticmethod
    def _insert_chunk(connection: sqlite3.Connection, chunk: Chunk) -> None:
        connection.execute(
            """
            INSERT INTO chunks (chunk_id, doc_id, section_title, text_sha256, chunk_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                chunk.chunk_id,
                chunk.doc_id,
                chunk.metadata.section_title,
                chunk.text_sha256,
                json.dumps(chunk.model_dump(mode="json"), sort_keys=True),
            ),
        )

