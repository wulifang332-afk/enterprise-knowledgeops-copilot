from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import AppSettings
from backend.app.ingestion.service import IngestionService


def main() -> int:
    settings = AppSettings(project_root=PROJECT_ROOT)
    service = IngestionService(settings=settings)
    summary = service.ingest_all_raw()
    print(json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True))
    return 1 if summary.failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())

