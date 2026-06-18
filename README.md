# Enterprise KnowledgeOps Copilot

企业知识库自动化构建与 GraphRAG-ready 智能应用路线图

This project is an Enterprise KnowledgeOps platform, not a generic chatbot.

The current build includes the accepted MVP-0 retrieval baseline plus Phase 4 graph inspection. It turns synthetic enterprise documents into validated, chunked, searchable, citation-traceable, and graph-inspectable knowledge assets. The query-style search box and graph pages in Streamlit are inspection workspaces, not a chatbot.

## Current Capabilities Through Phase 4

- Ingest 8 synthetic enterprise Markdown documents from `data/raw/`.
- Validate required metadata with Pydantic v2 schemas.
- Generate deterministic document sections and chunk IDs.
- Persist a local SQLite registry and processed JSON artifacts.
- Build BM25, Chroma vector, and hybrid retrieval indexes.
- Search through FastAPI and Streamlit.
- Inspect BM25, vector, and hybrid scores.
- Inspect citations, quote hashes, offsets, and source chunks.
- Run a deterministic retrieval evaluation set.
- Extract a deterministic rule-based knowledge graph from processed chunks.
- Persist a local NetworkX graph artifact under `data/graph/`.
- Inspect graph nodes, edges, neighborhoods, relation types, source chunks, and evidence quotes through FastAPI and Streamlit Graph Explorer.

## Not Implemented Yet

- `/api/v1/query`
- Answer generation
- GraphRAG answer synthesis
- Guardrails
- Access-control simulation
- Feedback loop
- Full evaluation dashboard
- Neo4j adapter

These are planned for later phases and are intentionally absent from the current graph-inspection build.

## Setup

Use Python 3.11 or newer. In this local environment, use `python`, not `python3`, because `python3` maps to Python 3.9.

```bash
cd enterprise-knowledgeops-copilot
python --version
```

Install runtime and test dependencies if needed:

```bash
python -m pip install -e ".[dev]"
```

The app runs without external API keys. Mock embeddings are deterministic and local.

## Core Commands

Run tests:

```bash
python -m pytest
```

Ingest sample documents:

```bash
python scripts/ingest_sample_docs.py
```

Rebuild indexes:

```bash
python scripts/rebuild_indexes.py
```

Rebuild the graph:

```bash
python scripts/rebuild_graph.py
```

Run retrieval evaluation:

```bash
python scripts/run_retrieval_eval.py
```

Start FastAPI:

```bash
uvicorn backend.main:app --reload
```

Start Streamlit:

```bash
streamlit run dashboard/streamlit_app.py
```

Run the full MVP-0 demo checkpoint:

```bash
python scripts/demo_mvp0_check.py
```

## Current Verification Results

Latest checkpoint:

```text
Tests: 40 passed
BM25 hit_rate@5: 20/20, 100%
Vector hit_rate@5: 20/20, 100%
Hybrid hit_rate@5: 20/20, 100%
Graph rebuild: 96 nodes, 207 edges, 40 source chunks
MVP-0 demo checkpoint passed
```

The 100% retrieval score is on a deterministic synthetic evaluation set. It is useful for regression testing and portfolio demonstration, but it is not a production accuracy claim.

## Example Search Queries

- `Vendor Payment Request Form`
- `ServiceNow Severity 1 15 minutes`
- `APAC EU cross-border transfer approval`

## Example Graph Objects

- Node: `Vendor Payment Request Form`
- Node: `ServiceNow`
- Node: `Severity 1`
- Node: `15 minutes`
- Node: `DPO`
- Edge: `Vendor Payment Approval Policy REQUIRES Vendor Payment Request Form`
- Edge: `IT Incident Escalation SOP USES_SYSTEM ServiceNow`
- Edge: `Severity 1 HAS_TIME_REQUIREMENT 15 minutes`
- Edge: `Cross-border Data Handling Policy ESCALATES_TO DPO`

## Local URLs

After starting the services:

- FastAPI: `http://127.0.0.1:8000`
- Streamlit: `http://localhost:8501`

## Documentation

- [Demo Guide](docs/demo.md)
- [API Reference](docs/api.md)
- [Architecture](docs/architecture.md)
- [Retrieval Evaluation](docs/evaluation.md)
- [Implementation Notes](docs/implementation_notes.md)

## Known Limitations

- Synthetic data only.
- Mock embeddings are lexical/hash based.
- No answer generation yet.
- No GraphRAG answer synthesis yet.
- No guardrails or access-control simulation yet.
- No feedback loop yet.
- No full evaluation dashboard yet.
- No Neo4j adapter yet.
- Graph extraction is deterministic and rule-based, tuned for the synthetic demo corpus, and not production-grade information extraction.
- Graph endpoints are for inspection only, not question answering.
- FastAPI must be running before the Streamlit dashboard can call the backend.
- Generated local artifacts such as SQLite databases, audit logs, indexes, and graph JSON can be regenerated from the included synthetic documents.
