from __future__ import annotations

import json
import shutil
from pathlib import Path

from backend.app.core.settings import AppSettings
from backend.app.retrieval.bm25 import BM25Index
from backend.app.retrieval.corpus import ProcessedCorpus
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.vector import ChromaVectorIndex
from scripts.run_retrieval_eval import evaluate

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET = PROJECT_ROOT / "evaluation" / "datasets" / "phase2_retrieval_cases.json"


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    return AppSettings(project_root=tmp_path, data_dir=data_dir)


def build_indexes(settings: AppSettings) -> None:
    chunks = ProcessedCorpus(settings).load()
    BM25Index(settings).build(chunks)
    ChromaVectorIndex(settings).build(chunks)


def test_bm25_exact_term_retrieval_for_enterprise_terms(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    build_indexes(settings)
    bm25 = BM25Index(settings)

    cases = {
        "Vendor Payment Request Form": "vendor-payment-approval-policy-v1-0",
        "ServiceNow": "it-incident-escalation-sop-v1-0",
        "USD 50,000": "vendor-payment-approval-policy-v1-0",
        "HRIS": "employee-onboarding-sop-v1-0",
        "APAC EU": "cross-border-data-policy-v1-0"
    }
    for query, expected_doc_id in cases.items():
        result_ids = [candidate.chunk_id for candidate in bm25.search(query, top_k=5)]
        docs = {ProcessedCorpus(settings).by_chunk_id()[chunk_id].chunk.doc_id for chunk_id in result_ids}
        assert expected_doc_id in docs


def test_chroma_vector_index_builds_and_hybrid_returns_cited_results(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    build_indexes(settings)

    vector_results = ChromaVectorIndex(settings).search("AI tool confidential personal data", top_k=5)
    assert vector_results
    assert settings.chroma_index_dir.exists()

    hybrid_results = HybridRetriever(settings).search(
        "vendor payments above USD 50,000 Finance Director CFO",
        top_k=5,
    )
    assert hybrid_results
    top = hybrid_results[0]
    assert top.doc_id == "vendor-payment-approval-policy-v1-0"
    assert top.citation.citation_id == "CIT-1"
    assert top.citation.quote
    assert top.citation.start_char < top.citation.end_char
    assert len(top.citation.quote_hash) == 64


def test_retrieval_eval_hit_rate_and_hybrid_baseline_rule(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    build_indexes(settings)

    result = evaluate(settings, DATASET, top_k=5)

    assert result["metrics"]["hybrid"]["hit_rate_at_5"] >= 0.80
    assert result["hybrid_not_below_baselines"]


def test_vector_rebuild_preserves_previous_valid_index_on_failure(tmp_path: Path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    chunks = ProcessedCorpus(settings).load()
    vector = ChromaVectorIndex(settings)
    vector.build(chunks)
    manifest_before = json.loads((settings.indexes_dir / "chroma_manifest.json").read_text(encoding="utf-8"))

    def fail_build_into(*args, **kwargs):
        raise RuntimeError("simulated build failure")

    monkeypatch.setattr(vector, "_build_into", fail_build_into)
    try:
        vector.build(chunks)
    except Exception:
        pass

    manifest_after = json.loads((settings.indexes_dir / "chroma_manifest.json").read_text(encoding="utf-8"))
    assert manifest_after == manifest_before
    assert ChromaVectorIndex(settings).search("Vendor Payment Request Form", top_k=1)

