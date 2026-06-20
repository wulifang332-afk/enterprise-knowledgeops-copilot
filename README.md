# Enterprise KnowledgeOps Copilot

Enterprise KnowledgeOps Copilot is a local-first enterprise AI portfolio project. It is not a generic chatbot. It turns a synthetic enterprise document corpus into searchable, citation-backed, graph-inspectable, query-routable, answerable, evaluable, and feedback-governed knowledge assets.

The project demonstrates how an AI Product Manager, Enterprise AI Solution Consultant, RAG Application Engineer, or GraphRAG/Product Engineer could design and ship a governed knowledge operations platform: ingestion, metadata governance, deterministic chunking, hybrid retrieval, citations, knowledge graph inspection, query planning, grounded answer generation, evaluation, and feedback governance.

## What This Is

- A local KnowledgeOps platform for synthetic enterprise policies and SOPs.
- A reproducible FastAPI + Streamlit demo with deterministic local behavior.
- A portfolio-grade proof of concept for RAG, graph inspection, evaluation, and governance workflows.
- A system that emphasizes traceability, citations, auditability, and quality control.

## What This Is Not

- Not a generic chatbot.
- Not a production GraphRAG system.
- Not production-ready enterprise search.
- Not connected to real enterprise data.
- Not an authenticated workflow system with RBAC, SSO, ticketing, monitoring, or online experimentation.
- Not an LLM-as-a-judge evaluation system.

## Current Capabilities

- Ingest 8 synthetic enterprise Markdown documents from `data/raw/`.
- Validate metadata with Pydantic v2 schemas.
- Generate deterministic sections, chunks, chunk IDs, offsets, and hashes.
- Persist a local SQLite registry and processed JSON artifacts.
- Build BM25, Chroma vector, and hybrid retrieval indexes.
- Search with BM25, vector, or hybrid retrieval through FastAPI and Streamlit.
- Inspect scores, source chunks, citation IDs, quote hashes, and offsets.
- Extract a deterministic rule-based knowledge graph from processed chunks.
- Persist a local NetworkX graph artifact under ignored `data/graph/`.
- Inspect graph nodes, edges, neighborhoods, relation types, source chunks, and evidence quotes.
- Route enterprise questions into deterministic intents and evidence paths.
- Return `/api/v1/query` evidence packs by default.
- Optionally generate deterministic citation-grounded answers with `generate_answer=true`.
- Refuse out-of-scope, unsupported, or insufficient-evidence requests without fabricating answers.
- Run deterministic retrieval and Phase 6 quality evaluations.
- Inspect evaluation metrics and case-level failures in Streamlit.
- Capture local feedback, triage review status, and link feedback to evaluation case IDs manually.

## Architecture Overview

```text
Raw enterprise docs
  -> secure ingestion + metadata validation
  -> deterministic sections and chunks
  -> SQLite registry + processed JSON
  -> BM25 / Chroma / hybrid retrieval indexes
  -> citation builder
  -> rule-based knowledge graph
  -> query planner and evidence pack
  -> deterministic grounded answer composer
  -> evaluation harness
  -> local feedback governance loop
```

Important implementation boundaries:

- Graph extraction is deterministic and rule-based.
- Answer composition is deterministic and local, not external LLM synthesis.
- The corpus is synthetic and intentionally small.
- Graph facts guide inspection and evidence routing, but the project does not claim production GraphRAG answer synthesis.
- The default demo runs without external API keys.

## Demo Workflow

1. Install dependencies.
2. Rebuild retrieval indexes.
3. Rebuild the graph.
4. Start FastAPI.
5. Start Streamlit.
6. Ingest and inspect documents.
7. Search with citations.
8. Explore graph nodes and edges.
9. Build a Query Planner evidence pack.
10. Generate a citation-grounded answer.
11. Run deterministic evaluation.
12. Inspect the Evaluation Dashboard.
13. Submit feedback.
14. Review the Feedback Governance Dashboard.

See [docs/demo.md](docs/demo.md) for the full walkthrough.

## Quick Start

Use Python 3.11 or newer. In this local environment, use `python`, not `python3`, because `python3` may map to Python 3.9.

```bash
cd enterprise-knowledgeops-copilot
python --version
python -m pip install -e ".[dev]"
```

Run the core checks and generated local artifacts:

```bash
python -m pytest
python scripts/rebuild_indexes.py
python scripts/rebuild_graph.py
python scripts/run_retrieval_eval.py
python scripts/run_phase6_eval.py
python scripts/demo_mvp0_check.py
```

Start the local apps:

```bash
uvicorn backend.main:app --reload
streamlit run dashboard/streamlit_app.py
```

Local URLs:

- FastAPI: `http://127.0.0.1:8000`
- Streamlit: `http://localhost:8501`

## API Highlights

- `POST /api/v1/ingest`: ingest all or selected raw documents.
- `GET /api/v1/documents`: browse document metadata.
- `GET /api/v1/chunks`: browse chunks and offsets.
- `POST /api/v1/search`: run BM25, vector, or hybrid search.
- `POST /api/v1/graph/rebuild`: rebuild graph artifacts from processed chunks.
- `GET /api/v1/graph/nodes`: inspect graph nodes.
- `GET /api/v1/graph/edges`: inspect graph edges and evidence.
- `GET /api/v1/graph/neighborhood`: inspect node neighborhoods.
- `POST /api/v1/query`: return an evidence pack and optionally a citation-grounded answer.
- `POST /api/v1/evaluation/run`: run deterministic Phase 6 evaluation.
- `GET /api/v1/evaluation/latest`: load the latest local evaluation report.
- `POST /api/v1/feedback`: submit local governance feedback.
- `GET /api/v1/feedback`: list and filter feedback records.
- `PATCH /api/v1/feedback/{feedback_id}`: triage feedback.

See [docs/api.md](docs/api.md) for readable examples.

## Evaluation And Governance

Current deterministic verification baseline:

```text
Tests: 118 passed
BM25 retrieval eval: 20/20
Vector retrieval eval: 20/20
Hybrid retrieval eval: 20/20
Graph rebuild: 96 nodes, 207 edges, 40 source chunks
Phase 6 evaluation: 22/22 cases passed (17 core, 5 holdout)
Fabricated-answer rate: 0%
Clean-clone verification: passed through Phase 7
```

Interpretation:

- These metrics are deterministic regression checks over a controlled synthetic corpus.
- They are useful for portfolio demonstration and reproducibility.
- They are not production accuracy, semantic faithfulness, compliance, or safety claims.
- Feedback is stored locally as JSONL and can support future manual evaluation curation.
- Feedback does not automatically mutate the evaluation dataset.

## Version History

| Phase | Tag | Scope |
|---|---|---|
| MVP-0 / Phase 1 | `v0.1.0-mvp0` | Repository structure, synthetic docs, ingestion, metadata validation, deterministic chunking |
| Phase 2 | `v0.1.0-mvp0` | BM25, Chroma vector index, hybrid retrieval, citation output, retrieval evaluation |
| Phase 3 | `v0.1.0-mvp0` | FastAPI + Streamlit MVP for ingestion, document/chunk browsing, search, citation inspection |
| Phase 4 | `v0.2.2-graph` | Rule-based graph extraction, NetworkX graph store, graph inspection APIs, Graph Explorer |
| Phase 5A | `v0.3.1-query-evidence` | Query intent classification, routing, evidence packs, structured refusal |
| Phase 5B | `v0.4.0-grounded-answer` | Optional deterministic citation-grounded answer generation |
| Phase 6 | `v0.5.0-evaluation-dashboard` | Evaluation harness, core/holdout dataset, metrics, Evaluation Dashboard |
| Phase 7 | `v0.6.0-feedback-governance` | Local feedback capture, review queue, governance dashboard, feedback audit events |
| Phase 8 | planned `v1.0.0-portfolio` | Final portfolio packaging, docs, release notes, clean demo narrative |

## Tech Stack

- Python 3.11+
- FastAPI
- Streamlit
- Pydantic v2
- SQLite
- BM25 local implementation
- Chroma local persistent vector index
- Deterministic mock embeddings
- NetworkX graph backend
- Pytest

## Documentation

- [Demo Guide](docs/demo.md)
- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Evaluation Reference](docs/evaluation.md)
- [Implementation Notes](docs/implementation_notes.md)
- [Portfolio Summary](docs/portfolio_summary.md)
- [Final Checklist](docs/final_checklist.md)
- [Release Notes Draft](docs/releases/v1.0.0-portfolio.md)

## Example Prompts

Search:

- `Vendor Payment Request Form`
- `ServiceNow Severity 1 15 minutes`
- `APAC EU cross-border transfer approval`

Query Planner:

- `Which approval form is required for vendor payments?`
- `What system is used for Severity 1 incidents?`
- `How does cross-border data approval work between APAC and EU?`
- `What is the capital of France?`

Use `generate_answer=true` to request a citation-grounded answer. Without that flag, `/api/v1/query` returns the evidence pack only.

## Limitations

- Synthetic enterprise corpus only.
- Deterministic local answer composer, not external LLM synthesis.
- Rule-based graph extraction tuned for the synthetic corpus.
- Deterministic evaluation checks, not semantic faithfulness proof.
- Local JSONL feedback store, not a production workflow engine.
- No authentication, RBAC, SSO, ticketing integration, or production human review workflow.
- No production monitoring, online experimentation, retraining, or prompt optimization.
- No Neo4j adapter.
- No real enterprise data integration.
- Not production-ready.

## Future Work

- Optional external LLM provider integration while preserving deterministic mock mode.
- Stronger entity/relation extraction and graph normalization.
- Access-control simulation and advanced enterprise guardrails.
- Optional Neo4j adapter.
- Human review workflow integration.
- Larger evaluation corpus and semantic/faithfulness evaluation.
- Deployment packaging after local portfolio release.

## Portfolio / Resume Summary

Built a local-first Enterprise KnowledgeOps Copilot that converts synthetic enterprise policies and SOPs into governed knowledge assets with metadata validation, deterministic chunking, hybrid retrieval, citation traceability, rule-based graph inspection, query planning, citation-grounded answer generation, deterministic evaluation, and local feedback governance.
