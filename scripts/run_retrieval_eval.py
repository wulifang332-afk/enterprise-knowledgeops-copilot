from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.settings import AppSettings
from backend.app.retrieval.bm25 import BM25Index
from backend.app.retrieval.corpus import ProcessedCorpus
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.vector import ChromaVectorIndex

DEFAULT_DATASET = PROJECT_ROOT / "evaluation" / "datasets" / "phase2_retrieval_cases.json"


def load_cases(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def hit_at_k(results: list, expected_doc_ids: list[str], expected_chunk_ids: list[str]) -> bool:
    result_doc_ids = {result.doc_id for result in results}
    result_chunk_ids = {result.chunk_id for result in results}
    if expected_chunk_ids and result_chunk_ids.intersection(expected_chunk_ids):
        return True
    return bool(result_doc_ids.intersection(expected_doc_ids))


def evaluate(settings: AppSettings, dataset_path: Path, *, top_k: int = 5) -> dict:
    cases = load_cases(dataset_path)
    bm25 = BM25Index(settings)
    vector = ChromaVectorIndex(settings)
    hybrid = HybridRetriever(settings, bm25_index=bm25, vector_index=vector)
    corpus_by_id = ProcessedCorpus(settings).by_chunk_id()

    metrics = {
        "bm25": {"hits": 0, "total": len(cases)},
        "vector": {"hits": 0, "total": len(cases)},
        "hybrid": {"hits": 0, "total": len(cases)},
    }
    case_results: list[dict] = []
    for case in cases:
        query = case["query"]
        expected_doc_ids = case.get("expected_doc_ids", [])
        expected_chunk_ids = case.get("expected_chunk_ids", [])

        bm25_ids = [candidate.chunk_id for candidate in bm25.search(query, top_k=top_k)]
        vector_ids = [candidate.chunk_id for candidate in vector.search(query, top_k=top_k)]
        hybrid_results = hybrid.search(query, top_k=top_k)

        bm25_hit = bool(
            {corpus_by_id[chunk_id].chunk.doc_id for chunk_id in bm25_ids}.intersection(expected_doc_ids)
            or set(bm25_ids).intersection(expected_chunk_ids)
        )
        vector_hit = bool(
            {corpus_by_id[chunk_id].chunk.doc_id for chunk_id in vector_ids}.intersection(expected_doc_ids)
            or set(vector_ids).intersection(expected_chunk_ids)
        )
        hybrid_hit = hit_at_k(hybrid_results, expected_doc_ids, expected_chunk_ids)

        metrics["bm25"]["hits"] += int(bm25_hit)
        metrics["vector"]["hits"] += int(vector_hit)
        metrics["hybrid"]["hits"] += int(hybrid_hit)
        case_results.append(
            {
                "case_id": case["case_id"],
                "query": query,
                "expected_doc_ids": expected_doc_ids,
                "expected_chunk_ids": expected_chunk_ids,
                "bm25_hit": bm25_hit,
                "vector_hit": vector_hit,
                "hybrid_hit": hybrid_hit,
                "hybrid_top_chunks": [result.chunk_id for result in hybrid_results],
            }
        )

    for values in metrics.values():
        values["hit_rate_at_5"] = values["hits"] / values["total"] if values["total"] else 0.0

    return {
        "dataset": str(dataset_path),
        "top_k": top_k,
        "metrics": metrics,
        "hybrid_not_below_baselines": (
            metrics["hybrid"]["hit_rate_at_5"] >= metrics["bm25"]["hit_rate_at_5"]
            and metrics["hybrid"]["hit_rate_at_5"] >= metrics["vector"]["hit_rate_at_5"]
        ),
        "cases": case_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    settings = AppSettings(project_root=PROJECT_ROOT)
    result = evaluate(settings, args.dataset, top_k=args.top_k)
    print(json.dumps(result, indent=2, sort_keys=True))
    hybrid_rate = result["metrics"]["hybrid"]["hit_rate_at_5"]
    if hybrid_rate < 0.80 or not result["hybrid_not_below_baselines"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

