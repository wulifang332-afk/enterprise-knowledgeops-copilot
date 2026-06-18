# Enterprise KnowledgeOps Copilot

企业知识库自动化构建与 GraphRAG-ready 智能应用路线图

This project is an Enterprise KnowledgeOps platform, not a generic chatbot.

The current MVP-0 focuses on ingestion, retrieval, citations, and a KnowledgeOps dashboard. It turns synthetic enterprise documents into validated, chunked, searchable, and citation-traceable knowledge assets. The query-style search box in Streamlit is only a retrieval workspace for inspecting metadata, chunks, scores, and citations.

## Current MVP-0 Capabilities

- Ingest 8 synthetic enterprise Markdown documents from `data/raw/`.
- Validate required metadata with Pydantic v2 schemas.
- Generate deterministic document sections and chunk IDs.
- Persist a local SQLite registry and processed JSON artifacts.
- Build BM25, Chroma vector, and hybrid retrieval indexes.
- Search through FastAPI and Streamlit.
- Inspect BM25, vector, and hybrid scores.
- Inspect citations, quote hashes, offsets, and source chunks.
- Run a deterministic retrieval evaluation set.

## Not Implemented Yet

- `/api/v1/query`
- Answer generation
- GraphRAG
- Graph extraction
- Guardrails
- Access-control simulation
- Feedback loop
- Full evaluation dashboard

These are planned for later phases and are intentionally absent from MVP-0.

## Setup

Use Python 3.11 or newer. In this local environment, use `python`, not `python3`, because `python3` maps to Python 3.9.

```bash
cd enterprise-knowledgeops-copilot
python --version
```

Install dependencies if needed:

```bash
python -m pip install -e .
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
Tests: 28 passed
BM25 hit_rate@5: 20/20, 100%
Vector hit_rate@5: 20/20, 100%
Hybrid hit_rate@5: 20/20, 100%
MVP-0 demo checkpoint passed
```

The 100% retrieval score is on a deterministic synthetic evaluation set. It is useful for regression testing and portfolio demonstration, but it is not a production accuracy claim.

## Example Search Queries

- `Vendor Payment Request Form`
- `ServiceNow Severity 1 15 minutes`
- `APAC EU cross-border transfer approval`

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
- No GraphRAG yet.
- No graph extraction yet.
- No guardrails or access-control simulation yet.
- No feedback loop yet.
- No full evaluation dashboard yet.
- FastAPI must be running before the Streamlit dashboard can call the backend.
- Generated local artifacts such as SQLite databases, audit logs, and indexes can be regenerated from the included synthetic documents.
