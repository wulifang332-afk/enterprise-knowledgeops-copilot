# Enterprise KnowledgeOps Studio

## Purpose

Phase 9A adds a React/Vite product-facing frontend for Enterprise KnowledgeOps Copilot. The Studio gives product-facing visibility across the KnowledgeOps lifecycle: workspace inventory, citation-backed search, graph inspection, query routing, evaluation metrics, and feedback governance.

FastAPI remains the backend API and source of truth. Streamlit remains the technical evaluation and governance dashboard layer. The architecture remains local-first, with the Studio acting as a portfolio/product demo layer rather than production infrastructure.

## Local Architecture

| Layer | Role |
|---|---|
| React/Vite Studio | Product-facing frontend for browsing local KnowledgeOps state |
| FastAPI API | Backend contract for documents, retrieval, graph, query, evaluation, and feedback |
| Local artifacts | SQLite registry, processed documents, retrieval indexes, graph artifact, evaluation reports, feedback JSONL |
| Streamlit dashboards | Technical workflow dashboards for inspection, evaluation, and governance |

No production infrastructure is added in Phase 9A. The Studio uses existing local APIs and gracefully renders fallback states when the backend is unavailable.

## Studio Pages

| Route | Purpose | APIs Consumed | Read-Only / Mutation Boundary |
|---|---|---|---|
| `/` | Landing page with lifecycle overview and summary metrics | Workspace and evaluation summaries | Read-only overview; no workflow actions |
| `/workspace` | Product-facing view of documents, chunks, and pipeline state | Workspace summary and document metadata | Read-only inventory; no upload, edit, delete, or rebuild actions |
| `/search` | Citation-backed retrieval transparency | Search API | Submits retrieval queries only; citations are returned by the backend |
| `/graph` | Graph nodes, edges, relation evidence, and selected neighborhoods | Graph read APIs | Read-only graph inspection; no graph rebuild or graph mutation |
| `/query` | Query routing and evidence-pack transparency | Query API | Submits query requests; no frontend answer generation or routing logic |
| `/evaluation` | Evaluation summary, latest report, and case visibility | Evaluation read APIs | Read-only evaluation inspection; no evaluation run action |
| `/governance` | Feedback records and review status visibility | Feedback list API | Read-only governance view; no feedback submit or update action |

## Page-To-API Mapping

| Route | Backend APIs |
|---|---|
| `/` | `GET /api/v1/workspace/summary`, `GET /api/v1/evaluation/summary` |
| `/workspace` | `GET /api/v1/workspace/summary`, `GET /api/v1/documents` |
| `/search` | `POST /api/v1/search` |
| `/graph` | `GET /api/v1/graph/nodes`, `GET /api/v1/graph/edges`, `GET /api/v1/graph/neighborhood` |
| `/query` | `POST /api/v1/query` |
| `/evaluation` | `GET /api/v1/evaluation/summary`, `GET /api/v1/evaluation/latest`, `GET /api/v1/evaluation/cases` |
| `/governance` | `GET /api/v1/feedback` |

## Screenshots

Studio screenshots are stored as committed portfolio assets:

| Page | Screenshot |
|---|---|
| Landing | `docs/assets/studio/studio-landing.png` |
| Workspace | `docs/assets/studio/studio-workspace.png` |
| Search & Citations | `docs/assets/studio/studio-search.png` |
| Query Planner | `docs/assets/studio/studio-query.png` |
| Evaluation Center | `docs/assets/studio/studio-evaluation.png` |
| Governance Center | `docs/assets/studio/studio-governance.png` |
| Graph Explorer | `docs/assets/studio/studio-graph.png` |

## Running Locally

The backend is optional for graceful fallback UI. To see live metrics, search results, graph data, evaluation artifacts, and feedback records, run the FastAPI backend before using the Studio.

```bash
cd frontend
npm install
npm run dev
npm run build
npm run test:e2e
npm run screenshots:studio
```

Default local URL:

```text
http://127.0.0.1:5173
```

## Read-Only Boundaries

The Studio is intentionally visibility-first:

- no upload, edit, delete, or rebuild actions
- no graph rebuild from Studio
- no evaluation run from Studio
- no feedback submit or update from Studio
- no frontend-generated citations
- no frontend-generated answers
- no frontend-generated evaluation metrics

Backend services remain responsible for retrieval, citation construction, graph evidence, query planning, grounded answer generation, evaluation metrics, and feedback governance behavior.

## Non-Goals / Limitations

- Synthetic corpus only.
- Deterministic local evaluation, not production semantic evaluation.
- Local-first demo, not production infrastructure.
- No auth, RBAC, or SSO.
- No Neo4j, Redis, Kafka, Celery, Supabase/Postgres, or production deployment infrastructure.
- Studio does not replace Streamlit dashboards.
- Studio is portfolio-oriented and should not be treated as a production enterprise UI.
