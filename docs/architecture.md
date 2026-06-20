# Architecture Overview

Enterprise KnowledgeOps Copilot is a local-first portfolio implementation of an enterprise knowledge operations platform. The architecture turns synthetic policies and SOPs into structured, searchable, citation-backed, graph-inspectable, evaluable, and feedback-governed knowledge assets.

It is not a production GraphRAG system and not a generic chatbot. The current implementation is deterministic by default and runs without external API keys.

## End-To-End Flow

```text
Raw enterprise docs
  -> secure ingestion + metadata validation
  -> deterministic sections and chunks
  -> SQLite registry + processed JSON
  -> BM25 / Chroma / hybrid retrieval indexes
  -> citation builder
  -> rule-based knowledge graph
  -> query planner
  -> evidence pack
  -> deterministic grounded answer composer
  -> evaluation harness
  -> local feedback governance loop
```

## Component Responsibilities

| Layer | Responsibility | Local Artifact |
|---|---|---|
| Raw documents | Synthetic enterprise Markdown files | `data/raw/*.md` |
| Ingestion | Safe loading from `data/raw`, file validation, metadata parsing | SQLite + processed JSON |
| Metadata validation | Pydantic v2 validation for document and chunk metadata | `data/processed/*.json` |
| Section and chunking | Markdown heading parsing, deterministic chunk IDs, offsets, hashes | `data/processed/*.json` |
| Retrieval | BM25 exact-term index, Chroma vector index, hybrid score fusion | `data/indexes/` |
| Citation builder | Citation IDs, quotes, offsets, source files, quote hashes | API responses |
| Graph extraction | Rule-based entity/relation extraction from processed chunks | `data/graph/knowledge_graph.json` |
| Graph store | NetworkX graph persistence and neighborhood inspection | `data/graph/` |
| Query planner | Intent classification, route selection, evidence-pack construction | `/api/v1/query` |
| Answer composer | Optional deterministic citation-grounded answer from returned evidence | `/api/v1/query` |
| Evaluation | Versioned deterministic cases, metrics, JSON/Markdown reports | `data/evaluation/` |
| Feedback governance | Local feedback capture, review queue, triage, audit events | `data/feedback/`, `data/audit/` |
| API | FastAPI endpoints for all inspectable workflows | `backend/main.py` |
| Dashboard | Streamlit KnowledgeOps workflow pages | `dashboard/` |

## ASCII Architecture Diagram

```text
              +---------------------------+
              | data/raw/*.md             |
              | synthetic enterprise docs |
              +-------------+-------------+
                            |
                            v
              +---------------------------+
              | Secure Ingestion          |
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
              | deterministic IDs/offsets |
              +-------------+-------------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
 +-----------------------+     +---------------------------+
 | SQLite Registry       |     | data/processed/*.json     |
 | document/chunk index  |     | source of truth           |
 +-----------------------+     +-------------+-------------+
                                             |
                +----------------------------+----------------------------+
                |                            |                            |
                v                            v                            v
     +---------------------+      +----------------------+      +----------------------+
     | BM25 Index          |      | Chroma Vector Index  |      | Rule-Based Graph     |
     | exact terms         |      | mock embeddings      |      | Extraction           |
     +----------+----------+      +----------+-----------+      +----------+-----------+
                |                            |                             |
                +-------------+--------------+                             v
                              |                              +----------------------+
                              v                              | NetworkX Graph Store |
                   +----------------------+                  | nodes/edges/evidence |
                   | Hybrid Retrieval     |                  +----------+-----------+
                   | score fusion         |                             |
                   +----------+-----------+                             |
                              |                                         |
                              v                                         |
                   +----------------------+                             |
                   | Citation Builder     |                             |
                   | quote/offset/hash    |                             |
                   +----------+-----------+                             |
                              |                                         |
                              v                                         |
                   +----------------------+                             |
                   | Query Planner        |<----------------------------+
                   | route + evidence     |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | Evidence Pack        |
                   | retrieval + graph    |
                   +----------+-----------+
                              |
                              v
                   +----------------------+
                   | Answer Composer      |
                   | deterministic only   |
                   +----------+-----------+
                              |
              +---------------+---------------+
              |                               |
              v                               v
  +------------------------+      +-------------------------+
  | Evaluation Harness     |      | Feedback Governance     |
  | metrics/reports        |      | local review queue      |
  +-----------+------------+      +------------+------------+
              |                                |
              +---------------+----------------+
                              |
                              v
              +-------------------------------+
              | FastAPI + Streamlit Dashboard |
              | KnowledgeOps workflow         |
              +-------------------------------+
```

## Data Flow Details

1. Raw Markdown files are loaded only from `data/raw`.
2. YAML front matter is parsed, but generated fields such as `source_file` and `content_sha256` are derived by the system.
3. Documents are split into sections using Markdown headings.
4. Sections are chunked deterministically with stable IDs, offsets, and hashes.
5. Registry data is stored in SQLite and processed JSON is written to `data/processed`.
6. Retrieval and graph services read processed JSON as the source of truth.
7. BM25 and Chroma indexes are rebuilt from processed chunks.
8. Search results are fused and citations are built from source offsets.
9. Rule-based graph extraction creates nodes and edges with source chunk evidence.
10. Query planning classifies intent and selects retrieval, graph, combined evidence, or refusal routes.
11. Evidence packs preserve retrieval evidence, graph evidence, citations, limitations, and routing decisions.
12. Answer generation is opt-in and deterministic; it only uses returned evidence and refuses unsupported requests.
13. Evaluation runs versioned deterministic cases through the query service and writes ignored reports.
14. Feedback captures local governance observations and optional manual links to evaluation cases.

## Graph Layer

The graph layer is deterministic and rule-based. It extracts entities such as policies, SOPs, departments, roles, systems, forms, regions, thresholds, time requirements, data types, risk types, and processes. It extracts relation types such as `REQUIRES`, `OWNS`, `APPLIES_TO`, `USES_SYSTEM`, `HAS_TIME_REQUIREMENT`, `HAS_ACCESS_LEVEL`, `GOVERNS`, `ESCALATES_TO`, and fallback `MENTIONS`.

The graph layer is for inspection, lineage review, and evidence routing. It is not production-grade information extraction and does not independently answer questions.

## Query And Answer Layer

The query layer is governed rather than chat-first. It classifies enterprise questions, chooses a route, builds an evidence pack, and optionally composes a citation-grounded answer.

Default `/api/v1/query` behavior returns evidence only. When `generate_answer=true`, the deterministic answer composer uses returned citations and refuses if evidence is unavailable, out of scope, unsupported, or insufficient. It does not call external LLM APIs and does not perform production GraphRAG final-response synthesis.

## Evaluation Layer

The Phase 6 evaluation harness uses a versioned deterministic dataset with 17 core cases and 5 holdout cases. It checks retrieval hits, route and intent accuracy, citation subsets, required answer phrases, refusal behavior, and fabricated-answer signals.

Metrics are regression checks over a controlled synthetic corpus. They are not production accuracy or semantic faithfulness claims. The harness does not use an external LLM judge.

## Feedback Governance Layer

Phase 7 adds local feedback capture and triage. Feedback records include query context, request ID, route/status, answer/citation context, rating, issue taxonomy, review status, reviewer notes, optional evaluation-case links, and source metadata.

Feedback is persisted under ignored `data/feedback/` artifacts. Local audit logging is implemented for ingestion events and Phase 7 feedback governance events. Retrieval, query, graph, and evaluation activity are inspectable through their outputs and reports, but they are not currently written as audit events.

Feedback supports future manual evaluation curation but does not automatically mutate the evaluation dataset.

## Deliberate Non-Goals

- Production GraphRAG answer synthesis
- External LLM answer synthesis by default
- External LLM judge
- Production authentication, SSO, or RBAC
- Ticketing or SaaS workflow integration
- Production monitoring
- Online experimentation or A/B testing
- Neo4j backend
- Real enterprise data integration
