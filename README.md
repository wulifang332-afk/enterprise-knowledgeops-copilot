# Enterprise KnowledgeOps Copilot

Enterprise KnowledgeOps Copilot

Enterprise KnowledgeOps Copilot | Personal Project
Built a local-first enterprise knowledge platform with FastAPI and Streamlit, supporting document ingestion, metadata validation, deterministic chunking, BM25/vector/hybrid retrieval, citation inspection, rule-based knowledge graph extraction, graph exploration, query planning, structured evidence packs, and Phase 5B citation-grounded answer generation. `/api/v1/query` classifies enterprise questions, routes them to retrieval/graph evidence workflows, preserves evidence-pack behavior by default, and optionally composes deterministic answers only from returned citations. Out-of-scope, unsupported, and insufficient-evidence requests are refused instead of answered.

This is an Enterprise KnowledgeOps platform, not a generic chatbot.


## Current Capabilities Through Phase 5B

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
- Classify enterprise questions into deterministic query intents.
- Route questions to retrieval, graph, combined evidence, or structured refusal paths.
- Return `/api/v1/query` evidence packs with retrieval evidence, graph evidence, citations, limitations, and answer-generation status.
- Optionally generate citation-grounded answers when `generate_answer=true` and evidence is sufficient.
- Refuse out-of-scope, unsupported, or insufficient-evidence requests without fabricating an answer.
- Inspect evidence packs and optional grounded answers in the Streamlit Query Planner.

## Not Implemented Yet

- GraphRAG answer synthesis
- Advanced enterprise guardrails
- Access-control simulation
- Feedback loop
- Full evaluation dashboard
- Neo4j adapter

These are planned for later phases and are intentionally absent from the current citation-grounded evidence build. External LLM synthesis is not required for the default local demo.

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
Tests: 85 passed
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

## Example Query Planner Prompts

- `Which approval form is required for vendor payments?`
- `What system is used for Severity 1 incidents?`
- `How does cross-border data approval work between APAC and EU?`
- `What is the capital of France?`

Use `generate_answer=true` to request a citation-grounded answer. Without that flag, `/api/v1/query` returns the Phase 5A evidence pack only.

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
- Answer generation is deterministic and template-based; it is optimized for grounded portfolio demonstration, not conversational fluency.
- No GraphRAG answer synthesis yet.
- `/api/v1/query` returns evidence packs by default; answers are opt-in with `generate_answer=true`.
- No advanced guardrails or access-control simulation yet.
- No feedback loop yet.
- No full evaluation dashboard yet.
- No Neo4j adapter yet.
- Graph extraction is deterministic and rule-based, tuned for the synthetic demo corpus, and not production-grade information extraction.
- Graph endpoints are for inspection only, not question answering.
- FastAPI must be running before the Streamlit dashboard can call the backend.
- Generated local artifacts such as SQLite databases, audit logs, indexes, and graph JSON can be regenerated from the included synthetic documents.
