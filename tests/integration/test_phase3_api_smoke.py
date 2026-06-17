from __future__ import annotations

import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.api.dependencies import get_settings
from backend.app.core.settings import AppSettings
from backend.main import create_app

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_phase3_ingest_search_citation_inspection_smoke(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "raw", data_dir / "raw")
    settings = AppSettings(project_root=tmp_path, data_dir=data_dir)
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)

    ingest = client.post("/api/v1/ingest", json={"ingest_all": True, "rebuild_indexes": True})
    assert ingest.status_code == 200
    assert ingest.json()["failed_count"] == 0

    documents = client.get("/api/v1/documents", params={"limit": 200})
    assert documents.status_code == 200
    assert documents.json()["total"] == 8

    chunks = client.get("/api/v1/chunks", params={"doc_id": "vendor-payment-approval-policy-v1-0"})
    assert chunks.status_code == 200
    assert chunks.json()["total"] == 5

    for mode in ("bm25", "vector", "hybrid"):
        search = client.post(
            "/api/v1/search",
            json={
                "query": "vendor payments above USD 50,000 Finance Director CFO",
                "retrieval_mode": mode,
                "top_k": 5,
                "filters": {},
            },
        )
        assert search.status_code == 200
        payload = search.json()
        assert payload["results"]
        top = payload["results"][0]
        assert top["citation"]["quote"] == top["text"]
        assert top["citation"]["start_char"] < top["citation"]["end_char"]
        assert len(top["citation"]["quote_hash"]) == 64

