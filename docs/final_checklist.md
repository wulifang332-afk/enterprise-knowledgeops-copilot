# Final Portfolio Checklist

Run this checklist before creating the planned `v1.0.0-portfolio` tag.

## Verification Commands

```bash
python -m pytest
python scripts/rebuild_indexes.py
python scripts/rebuild_graph.py
python scripts/run_retrieval_eval.py
python scripts/run_phase6_eval.py
python scripts/demo_mvp0_check.py
```

Expected current results:

```text
118 tests passed
retrieval eval: BM25/vector/hybrid all 20/20
graph rebuild: 96 nodes, 207 edges, 40 source chunks
Phase 6 eval: 22/22 cases passed
MVP-0 demo checkpoint passed
```

## Startup Checks

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8014
streamlit run dashboard/streamlit_app.py --server.headless true --server.port 8514
```

Expected:

- FastAPI starts successfully.
- Streamlit starts successfully.
- Streamlit health endpoint returns `ok`.

## Documentation Checks

- README first screen says this is not a generic chatbot.
- README version table includes all public tags through `v0.6.0-feedback-governance` and planned `v1.0.0-portfolio`.
- Demo guide covers ingestion, search, graph, query, grounded answer, evaluation, feedback.
- API guide covers ingestion, documents/chunks/search, graph, query, evaluation, feedback.
- Evaluation docs state deterministic metrics are regression checks, not semantic faithfulness proof.
- Governance docs state feedback does not mutate evaluation datasets automatically.
- Limitations mention synthetic corpus, deterministic answer composer, rule-based graph, JSONL feedback, no auth/RBAC/SSO, no production monitoring, no Neo4j, and not production-ready.

## Git Hygiene Checks

Generated artifacts should remain ignored:

- `data/knowledgeops.db`
- `data/indexes/`
- `data/graph/knowledge_graph.json`
- `data/evaluation/latest_report.json`
- `data/evaluation/latest_report.md`
- `data/evaluation/history/*.json`
- `data/feedback/feedback.jsonl`
- `data/feedback/review_queue.json`
- `data/feedback/feedback_corrupt.jsonl`
- `data/audit/*.jsonl`
- `.pytest_cache/`
- `__pycache__/`

Trackable placeholders:

- `data/graph/.gitkeep`
- `data/indexes/.gitkeep`
- `data/evaluation/.gitkeep`
- `data/feedback/.gitkeep`

## Release Readiness

- Full verification commands pass.
- `git status --short` is clean after commit.
- Clean-clone verification passes.
- Create final tag only after review:

```bash
git tag -a v1.0.0-portfolio -m "Final portfolio release"
git push origin v1.0.0-portfolio
```

