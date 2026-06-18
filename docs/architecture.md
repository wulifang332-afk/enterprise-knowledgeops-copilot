# MVP-0 + Phase 4 Architecture

The current build is a local-first KnowledgeOps pipeline. It focuses on deterministic ingestion, metadata validation, chunk traceability, retrieval, citation inspection, graph extraction, graph persistence, and thin API/UI inspection layers.

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
- FastAPI: endpoints for ingest, documents, chunks, search, and graph inspection.
- Streamlit: dashboard pages for ingestion, knowledge exploration, and graph exploration.
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
10. FastAPI exposes ingestion, registry browsing, chunk browsing, retrieval, and graph inspection.
11. Streamlit provides the KnowledgeOps dashboard, including Graph Explorer.
12. `scripts/demo_mvp0_check.py` verifies the MVP-0 retrieval demo path from CLI.

## Graph Layer

Phase 4 graph extraction is deterministic and rule-based. It creates typed nodes for policies, SOPs, departments, roles, systems, forms, regions, thresholds, time requirements, data types, risk types, and processes. It creates typed edges such as `REQUIRES`, `OWNS`, `APPLIES_TO`, `USES_SYSTEM`, `HAS_TIME_REQUIREMENT`, `HAS_ACCESS_LEVEL`, `GOVERNS`, `ESCALATES_TO`, and fallback `MENTIONS`.

The graph layer is for inspection, lineage review, and portfolio demonstration. It is not production-grade information extraction and does not answer questions.

## Not Present Yet

- GraphRAG router
- `/api/v1/query`
- Answer generation
- GraphRAG answer synthesis
- Guardrails
- Feedback loop
- Full evaluation dashboard
- Neo4j adapter
