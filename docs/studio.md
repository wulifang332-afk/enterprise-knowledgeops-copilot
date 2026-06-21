# Enterprise KnowledgeOps Studio

## Purpose

Phase 9A adds a React/Vite product-facing frontend for Enterprise KnowledgeOps Copilot. The Studio gives product-facing visibility across the KnowledgeOps lifecycle: workspace inventory, citation-backed search, graph inspection, query routing, evaluation metrics, and feedback governance.

Phase 9B adds an Enterprise Readiness Layer. It introduces deterministic Access Policy Simulation, simulated enterprise personas, a `/readiness` page, and explicit opt-in persona simulation controls for Search and Query.

FastAPI remains the backend API and source of truth. Streamlit remains the technical evaluation and governance dashboard layer. The architecture remains local-first, with the Studio acting as a portfolio/product demo layer rather than production infrastructure.

## Local Architecture

| Layer | Role |
|---|---|
| React/Vite Studio | Product-facing frontend for browsing local KnowledgeOps state |
| FastAPI API | Backend contract for documents, retrieval, graph, query, evaluation, and feedback |
| Local artifacts | SQLite registry, processed documents, retrieval indexes, graph artifact, evaluation reports, feedback JSONL |
| Streamlit dashboards | Technical workflow dashboards for inspection, evaluation, and governance |

Phase 9B readiness APIs derive state from local artifacts and deterministic persona definitions. They do not run rebuilds, mutate local data, or add production access-control infrastructure.

No production infrastructure is added in Phase 9A or Phase 9B. The Studio uses existing local APIs and gracefully renders fallback states when the backend is unavailable.

## Studio Pages

| Route | Purpose | APIs Consumed | Read-Only / Mutation Boundary |
|---|---|---|---|
| `/` | Landing page with lifecycle overview and summary metrics | Workspace and evaluation summaries | Read-only overview; no workflow actions |
| `/workspace` | Product-facing view of documents, chunks, and pipeline state | Workspace summary and document metadata | Read-only inventory; no upload, edit, delete, or rebuild actions |
| `/search` | Citation-backed retrieval transparency with optional persona simulation | Search API and readiness access-policy API | Default search is unchanged; optional simulation applies generated metadata filters before retrieval |
| `/graph` | Graph nodes, edges, relation evidence, and selected neighborhoods | Graph read APIs | Read-only graph inspection; no graph rebuild or graph mutation |
| `/query` | Query routing and evidence-pack transparency with optional persona simulation | Query API and readiness access-policy API | Default query behavior is unchanged; optional simulation applies generated metadata filters before planning |
| `/readiness` | Enterprise readiness visibility and deterministic access-policy simulation | Readiness summary, personas, and access-policy APIs | Simulation-only; no auth, RBAC, SSO, login, or state mutation |
| `/evaluation` | Evaluation summary, latest report, and case visibility | Evaluation read APIs | Read-only evaluation inspection; no evaluation run action |
| `/governance` | Feedback records and review status visibility | Feedback list API | Read-only governance view; no feedback submit or update action |

## Page-To-API Mapping

| Route | Backend APIs |
|---|---|
| `/` | `GET /api/v1/workspace/summary`, `GET /api/v1/evaluation/summary` |
| `/workspace` | `GET /api/v1/workspace/summary`, `GET /api/v1/documents` |
| `/search` | `POST /api/v1/search`; optional `GET /api/v1/readiness/personas`, `POST /api/v1/readiness/access-policy` |
| `/graph` | `GET /api/v1/graph/nodes`, `GET /api/v1/graph/edges`, `GET /api/v1/graph/neighborhood` |
| `/query` | `POST /api/v1/query`; optional `GET /api/v1/readiness/personas`, `POST /api/v1/readiness/access-policy` |
| `/readiness` | `GET /api/v1/readiness/summary`, `GET /api/v1/readiness/personas`, `POST /api/v1/readiness/access-policy` |
| `/evaluation` | `GET /api/v1/evaluation/summary`, `GET /api/v1/evaluation/latest`, `GET /api/v1/evaluation/cases` |
| `/governance` | `GET /api/v1/feedback` |

## Enterprise Readiness Layer

Phase 9B is intentionally simulation-only. It answers a product question: given a simulated enterprise persona, what document metadata filters should apply, and why?

Readiness APIs:

- `GET /api/v1/readiness/personas`: returns deterministic simulated personas such as `global_admin`, `finance_manager_apac`, `hr_manager_eu`, `it_support_internal`, `legal_reviewer_global`, and `employee_public`.
- `POST /api/v1/readiness/access-policy`: returns `allowed_filters`, `denied_reasons`, `explanation`, and `simulation_only: true`.
- `GET /api/v1/readiness/summary`: returns local readiness status, corpus metadata distributions, graph/evaluation/governance availability, capabilities, and explicit non-goals.

The access-policy response can produce filters for existing metadata fields: `departments`, `regions`, `policy_types`, `owners`, and `access_levels`. These filters are generated before retrieval when the user explicitly enables persona simulation in Studio.

Default Search and Query behavior is unchanged. Persona simulation is opt-in, and Search/Query do not load readiness personas until the simulation control is enabled.

Phase 9B is not real authorization. It does not add login, sessions, authentication middleware, true RBAC, SSO, or production access enforcement.

## Screenshots

Studio screenshots are stored as committed portfolio assets:

| Page | Screenshot |
|---|---|
| Landing | `docs/assets/studio/studio-landing.png` |
| Workspace | `docs/assets/studio/studio-workspace.png` |
| Search & Citations | `docs/assets/studio/studio-search.png` |
| Query Planner | `docs/assets/studio/studio-query.png` |
| Readiness Center | `docs/assets/studio/studio-readiness.png` |
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
- no real auth/RBAC/SSO enforcement
- no automatic Search/Query filtering unless the user explicitly enables simulation

Backend services remain responsible for retrieval, citation construction, graph evidence, query planning, grounded answer generation, evaluation metrics, and feedback governance behavior.

## Non-Goals / Limitations

- Synthetic corpus only.
- Deterministic local evaluation, not production semantic evaluation.
- Local-first demo, not production infrastructure.
- No auth, RBAC, or SSO.
- Access Policy Simulation is not authorization.
- No Neo4j, Redis, Kafka, Celery, Supabase/Postgres, or production deployment infrastructure.
- Studio does not replace Streamlit dashboards.
- Studio is portfolio-oriented and should not be treated as a production enterprise UI.
