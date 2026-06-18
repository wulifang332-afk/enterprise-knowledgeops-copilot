# Implementation Notes

## Accepted Deviations

- Local BM25 implementation is used instead of `rank_bm25` because `rank_bm25` is not installed in this environment. The implementation includes BM25 scoring and the corrected normalization rule.
- `INVALID_REQUEST` was added to support clean FastAPI request validation errors.
- `POST /api/v1/ingest` rebuilds indexes by default for demo usability, so the UI supports ingest-to-search without an extra manual step.
- Use `python`, not `python3`, because this environment maps `python3` to Python 3.9 while the project requires Python 3.11+.
- Phase 4 graph extraction uses deterministic rule-based patterns instead of LLM extraction so tests and demos remain local and reproducible.
- Phase 4 uses NetworkX as the local graph backend. Neo4j remains a future optional adapter.
- Phase 4 suppresses generic `MENTIONS` edges when stronger same-pair relations exist and deduplicates document-level metadata edges to reduce graph noise.
- Processed JSON preserves an existing `ingested_at` value when the source content hash is unchanged. This keeps clean-clone demo runs from dirtying tracked processed artifacts while still allowing the SQLite registry to record a fresh ingestion timestamp.

## MVP-0 Checkpoint Commands

Use these commands before creating an MVP-0 commit:

```bash
python -m pytest
python scripts/run_retrieval_eval.py
python scripts/rebuild_graph.py
python scripts/demo_mvp0_check.py
```

The latest Phase 4 checkpoint reported 40 tests passing, BM25/vector/hybrid retrieval hit_rate@5 of 20/20, a graph rebuild of 96 nodes and 207 edges from 40 chunks, and a passing MVP-0 demo checkpoint.

## Current Known Limitations

- Synthetic data only.
- Mock embeddings are lexical/hash based and deterministic, not production semantic embeddings.
- Graph extraction is deterministic and rule-based.
- Graph extraction rules are tuned for the synthetic demo corpus.
- The graph layer is portfolio/demo information extraction, not production-grade IE.
- Graph endpoints are for inspection, not question answering.
- No answer generation yet.
- No GraphRAG answer synthesis yet.
- No access-control simulation yet.
- No guardrails yet.
- No feedback loop yet.
- No full evaluation dashboard yet.
- No Neo4j adapter yet.
- Streamlit pages require the FastAPI backend to be running.

## Local Artifacts

The following local artifacts are generated and can be regenerated:

- `data/knowledgeops.db`
- `data/knowledgeops.db-shm`
- `data/knowledgeops.db-wal`
- `data/indexes/`
- `data/graph/knowledge_graph.json`
- `data/audit/*.jsonl`

Processed JSON under `data/processed/` is currently kept as a demo artifact so retrieval and API examples can run immediately. It can be regenerated with:

```bash
python scripts/ingest_sample_docs.py
```

Graph JSON can be regenerated with:

```bash
python scripts/rebuild_graph.py
```
