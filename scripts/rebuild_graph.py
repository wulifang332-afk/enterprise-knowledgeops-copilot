from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import AppSettings
from backend.app.graph.service import GraphService


def rebuild_graph(settings: AppSettings) -> dict:
    result = GraphService(settings).rebuild()
    return {
        "status": "success",
        "node_count": result.node_count,
        "edge_count": result.edge_count,
        "source_chunk_count": result.source_chunk_count,
        "artifact_path": result.artifact_path,
    }


def main() -> int:
    settings = AppSettings(project_root=PROJECT_ROOT)
    result = rebuild_graph(settings)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
