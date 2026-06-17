from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import AppSettings
from backend.app.retrieval.indexing import IndexRebuildService


def rebuild_indexes(settings: AppSettings) -> dict:
    result = IndexRebuildService(settings).rebuild_all()
    return {
        "status": "success",
        "chunk_count": result.chunk_count,
        "bm25_index": result.bm25_index,
        "chroma_index": result.chroma_index,
    }


def main() -> int:
    settings = AppSettings(project_root=PROJECT_ROOT)
    result = rebuild_indexes(settings)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
