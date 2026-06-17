# MVP-0 Architecture

MVP-0 is a local-first KnowledgeOps pipeline. It focuses on deterministic ingestion, metadata validation, chunk traceability, retrieval, citation inspection, and a thin API/UI layer.

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
- FastAPI: Phase 3 endpoints for ingest, documents, chunks, and search.
- Streamlit: MVP dashboard for ingestion and knowledge exploration.
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
                         +------------------+------------------+
                         |                                     |
                         v                                     v
              +---------------------+              +----------------------+
              | BM25 Index          |              | Chroma Vector Index  |
              | exact terms         |              | mock embeddings      |
              +----------+----------+              +----------+-----------+
                         |                                    |
                         +----------------+-------------------+
                                          |
                                          v
                              +----------------------+
                              | Hybrid Retrieval     |
                              | score fusion         |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Citation Builder     |
                              | quote/offset/hash    |
                              +----------+-----------+
                                         |
                    +--------------------+--------------------+
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
6. Retrieval services read processed JSON as source of truth.
7. BM25 and Chroma indexes are rebuilt from processed chunks.
8. Search results are fused and citations are built from chunk offsets.
9. FastAPI exposes ingestion, registry browsing, chunk browsing, and retrieval.
10. Streamlit provides the MVP-0 KnowledgeOps dashboard.
11. `scripts/demo_mvp0_check.py` verifies the MVP-0 demo path from CLI.

## Not Present In MVP-0

- Graph extraction
- Graph store
- GraphRAG router
- `/api/v1/query`
- Answer generation
- Guardrails
- Feedback loop
- Full evaluation dashboard
