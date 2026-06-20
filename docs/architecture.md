# Phase 6 Architecture

The current Phase 6 build is a local-first KnowledgeOps pipeline. It focuses on deterministic ingestion, metadata validation, chunk traceability, retrieval, citation inspection, Phase 4 graph extraction and persistence, query planning, evidence-pack construction, citation-grounded answer generation, and deterministic quality evaluation.

## Current Components

- `data/raw`: synthetic enterprise Markdown documents.
- Ingestion service: secure loading from `data/raw` only.
- Metadata validation: Pydantic v2 schemas for document and chunk metadata.
- Section parser: Markdown heading-based section extraction.
- Chunking service: deterministic chunk IDs using heading occurrence and section path hash.
- SQLite registry: local document, section, and chunk registry.
- `data/processed`: JSON source of truth for retrieval services.
- BM25 index: local exact-term retrieval.
- Chroma vector index: persistent local vector index under `data/indexes`.
- Mock embedding provider: deterministic hash-based vectors.
- Hybrid retrieval: weighted BM25/vector fusion with metadata and recency boosts.
- Citation builder: quote, offsets, and quote hash from normalized source content.
- Rule-based graph extractor: deterministic entity and relation extraction from processed chunks.
- Graph schema: typed nodes and edges with source document/chunk lineage and evidence quotes.
- NetworkX graph store: local graph backend persisted under `data/graph/`.
- Graph rebuild script: `scripts/rebuild_graph.py`.
- Query planning service: deterministic intent classification, route selection, evidence-pack construction, and structured refusal.
- Deterministic answer composer: optional template-based citation-grounded answer generation when `generate_answer=true`.
- Evaluation service: versioned cases, deterministic checks, aggregate metrics, and JSON/Markdown reports.
- FastAPI: endpoints for ingest, documents, chunks, search, graph inspection, governed query planning/answer generation, and evaluation.
- Streamlit: dashboard pages for ingestion, knowledge exploration, graph exploration, query planning, and quality inspection.
- Demo check script: `scripts/demo_mvp0_check.py` runs tests, ingestion, index rebuild, and retrieval evaluation.

## ASCII Architecture Diagram

```text
              +---------------------------+
              | data/raw/*.md             |
              | synthetic enterprise docs |
              +-------------+-------------+
                            |
                            v
              +---------------------------+
              | Secure Document Loader    |
              | path/type/size validation |
              +-------------+-------------+
                            |
                            v
              +---------------------------+
              | Metadata Validation       |
              | Pydantic v2 schemas       |
              +-------------+-------------+
                            |
                            v
              +---------------------------+
              | Section Parser + Chunker  |
              | deterministic chunk IDs   |
              +-------------+-------------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
+-------------------------+   +---------------------------+
| SQLite Registry         |   | data/processed/*.json     |
| docs/sections/chunks    |   | retrieval source of truth |
+-------------------------+   +-------------+-------------+
                                            |
                                            v
                         +------------------+------------------+------------------+
                         |                                     |                  |
                         v                                     v                  v
              +---------------------+              +----------------------+  +----------------------+
              | BM25 Index          |              | Chroma Vector Index  |  | Rule-Based Graph     |
              | exact terms         |              | mock embeddings      |  | Extraction           |
              +----------+----------+              +----------+-----------+  +----------+-----------+
                         |                                    |                         |
                         +----------------+-------------------+                         v
                                          |                                  +----------------------+
                                          v                                  | NetworkX Graph Store |
                              +----------------------+                       | data/graph/*.json    |
                              | Hybrid Retrieval     |                       +----------+-----------+
                              | score fusion         |                                  |
                              +----------+-----------+                                  |
                                         |                                              |
                                         v                                              |
                              +----------------------+                                  |
                              | Citation Builder     |                                  |
                              | quote/offset/hash    |                                  |
                              +----------+-----------+                                  |
                                         |                                              |
                                         v
                              +----------------------+
                              | Query Evidence Pack  |
                              | routing + citations  |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Answer Composer      |
                              | deterministic only   |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Evaluation Harness   |
                              | cases/checks/reports |
                              +----------+-----------+
                                         |
                    +--------------------+--------------------+-------------------------+
                    |                                         |
                    v                                         v
          +------------------+                    +----------------------+
          | FastAPI          |                    | Streamlit Dashboard  |
          | /api/v1/*        |                    | KnowledgeOps UI      |
          +------------------+                    +----------------------+
```

## Data Flow

1. Raw Markdown files are loaded only from `data/raw`.
2. YAML front matter is parsed, but generated fields such as `source_file` and `content_sha256` are derived by the system.
3. Documents are split into sections using Markdown headings.
4. Sections are chunked deterministically.
5. Registry data is stored in SQLite and processed JSON is written to `data/processed`.
6. Retrieval and graph services read processed JSON as source of truth.
7. BM25 and Chroma indexes are rebuilt from processed chunks.
8. Search results are fused and citations are built from chunk offsets.
9. `scripts/rebuild_graph.py` extracts graph nodes and edges from processed chunks and persists a NetworkX graph artifact under `data/graph/`.
10. Phase 6 runs versioned cases through the existing query service and computes deterministic retrieval, routing, citation, grounding, and refusal metrics.
11. Reports are persisted under ignored `data/evaluation/` JSON/Markdown artifacts.
12. FastAPI exposes ingestion, registry browsing, chunk browsing, retrieval, graph inspection, query answering, and evaluation endpoints.
13. Streamlit provides the KnowledgeOps dashboard, including Graph Explorer, Query Planner, and Evaluation Dashboard.
14. CLI scripts verify retrieval, graph, Phase 6 quality checks, and the MVP-0 demo path.

## Phase 4 Graph Layer in the Phase 6 Release

The Phase 4 graph layer remains part of the current Phase 6 release. Graph extraction is deterministic and rule-based. It creates typed nodes for policies, SOPs, departments, roles, systems, forms, regions, thresholds, time requirements, data types, risk types, and processes. It creates typed edges such as `REQUIRES`, `OWNS`, `APPLIES_TO`, `USES_SYSTEM`, `HAS_TIME_REQUIREMENT`, `HAS_ACCESS_LEVEL`, `GOVERNS`, `ESCALATES_TO`, and fallback `MENTIONS`.

The graph layer is for inspection, lineage review, and portfolio demonstration. It is not production-grade information extraction and does not answer questions.

## Query Planning And Answer Layer

Phase 5A added deterministic query intent classification, evidence route selection, and evidence-pack construction. Phase 5B keeps that behavior as the default and adds opt-in citation-grounded answer generation when `generate_answer=true`.

The answer composer is deterministic and local. It selects returned retrieval citations, optionally uses graph evidence for routing and prioritization, and refuses when the evidence pack is out of scope, unsupported, missing citable evidence, or insufficient for the query. It does not call external LLM APIs and does not perform GraphRAG final-response synthesis.

## Evaluation Layer

Phase 6 adds a versioned deterministic evaluation dataset with core and independent holdout splits plus a reusable evaluation service. The service executes existing query behavior directly, compares actual outcomes with explicit expectations, aggregates split, per-intent, and top-level metrics, and writes local JSON/Markdown reports.

The evaluation layer checks inspectable signals such as expected sources, routes, citation subsets, required phrases, grounding summaries, refusal reasons, and fabricated-answer rate. Metrics with no applicable cases are represented as unavailable rather than 100%. It does not claim semantic faithfulness, use an LLM judge, collect online feedback, or monitor production traffic.

## Not Present Yet

- GraphRAG answer synthesis
- Advanced enterprise guardrails
- Feedback loop
- Human review workflow
- Production monitoring and online experimentation
- Neo4j adapter
