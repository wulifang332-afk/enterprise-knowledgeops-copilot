from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from backend.app.citations.builder import CitationBuilder, quote_hash
from backend.app.core.errors import KnowledgeOpsError
from backend.app.core.settings import AppSettings
from backend.app.retrieval.bm25 import BM25Index, tokenize_for_bm25
from backend.app.retrieval.corpus import ProcessedCorpus
from backend.app.retrieval.embeddings import MockEmbeddingProvider
from backend.app.retrieval.hybrid import HybridRetriever
from backend.app.retrieval.types import RetrieverCandidate
from backend.app.schemas.enums import ErrorCode

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def make_settings(tmp_path: Path) -> AppSettings:
    data_dir = tmp_path / "data"
    shutil.copytree(PROJECT_ROOT / "data" / "processed", data_dir / "processed")
    return AppSettings(project_root=tmp_path, data_dir=data_dir)


def test_bm25_normalization_handles_equal_scores() -> None:
    assert BM25Index.normalize_scores([2.0, 2.0]) == [1.0, 1.0]
    assert BM25Index.normalize_scores([0.0, 0.0]) == [0.0, 0.0]
    assert BM25Index.normalize_scores([1.0, 3.0]) == [0.0, 1.0]


def test_bm25_tokenizer_preserves_enterprise_terms() -> None:
    tokens = tokenize_for_bm25("APAC EU USD 50,000 Vendor Payment Request Form ServiceNow HRIS cross-border")
    assert "apac" in tokens
    assert "eu" in tokens
    assert "usd" in tokens
    assert "50,000" in tokens
    assert "50000" in tokens
    assert "vendor__payment__request" in tokens
    assert "servicenow" in tokens
    assert "hris" in tokens
    assert "cross-border" in tokens
    assert "crossborder" in tokens


def test_mock_embeddings_are_deterministic() -> None:
    provider = MockEmbeddingProvider(dimensions=384)
    first = provider.embed_query("Vendor Payment Request Form USD 50,000")
    second = provider.embed_query("Vendor Payment Request Form USD 50,000")
    different = provider.embed_query("HRIS onboarding Identity Management")

    assert first == second
    assert first != different
    assert len(first) == 384


def test_citation_builder_fields_offsets_and_hash(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    record = ProcessedCorpus(settings).by_chunk_id()[
        "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001"
    ]

    citation = CitationBuilder().build(record, rank=1)

    assert citation.citation_id == "CIT-1"
    assert citation.doc_id == "vendor-payment-approval-policy-v1-0"
    assert citation.chunk_id == record.chunk.chunk_id
    assert citation.title == "Vendor Payment Approval Policy"
    assert citation.section_title == "Required Documents"
    assert citation.source_file == "data/raw/vendor_payment_approval_policy.md"
    assert citation.version == "1.0"
    assert citation.quote == record.document_content[citation.start_char : citation.end_char]
    assert citation.quote_hash == quote_hash(citation.quote)


class FailingRetriever:
    def search(self, *args, **kwargs):
        raise KnowledgeOpsError(ErrorCode.INDEX_UNAVAILABLE, "forced failure")


class StaticRetriever:
    def __init__(self, chunk_id: str, score: float = 1.0) -> None:
        self.chunk_id = chunk_id
        self.score = score

    def search(self, *args, **kwargs):
        return [RetrieverCandidate(self.chunk_id, self.score, self.score, 1)]


def test_hybrid_degrades_to_bm25_when_vector_unavailable(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    chunk_id = "chk:vendor-payment-approval-policy-v1-0:approval-thresholds:01:c37a63ee91:001"
    retriever = HybridRetriever(
        settings,
        bm25_index=StaticRetriever(chunk_id),
        vector_index=FailingRetriever(),
    )

    results = retriever.search("USD 50,000", top_k=5)

    assert results[0].chunk_id == chunk_id
    assert results[0].vector_score is None
    assert results[0].bm25_score == 1.0


def test_hybrid_degrades_to_vector_when_bm25_unavailable(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    chunk_id = "chk:travel-reimbursement-policy-v1-0:claim-submission:01:4b056590ae:001"
    retriever = HybridRetriever(
        settings,
        bm25_index=FailingRetriever(),
        vector_index=StaticRetriever(chunk_id),
    )

    results = retriever.search("Concur Expense", top_k=5)

    assert results[0].chunk_id == chunk_id
    assert results[0].bm25_score is None
    assert results[0].vector_score == 1.0


def test_hybrid_raises_index_unavailable_when_both_indexes_fail(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    retriever = HybridRetriever(
        settings,
        bm25_index=FailingRetriever(),
        vector_index=FailingRetriever(),
    )

    with pytest.raises(KnowledgeOpsError) as exc:
        retriever.search("anything", top_k=5)

    assert exc.value.error_code == ErrorCode.INDEX_UNAVAILABLE

