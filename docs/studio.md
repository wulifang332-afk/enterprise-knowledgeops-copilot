# Enterprise KnowledgeOps Agent Workbench

The React/Vite frontend is a portfolio-facing Agent Workbench. It intentionally
uses a single-screen interface so the project is easier to explain in interviews.

The backend still owns ingestion, retrieval, citation construction, graph
evidence, query routing, evaluation, and feedback governance. Streamlit remains
the technical dashboard layer. The React Workbench is a product demo surface.

## What Changed

The previous multi-page Studio had separate screens for workspace, search,
query planning, readiness, evaluation, governance, and graph exploration. That
showed many features, but it made the project harder to understand quickly.

The new Workbench presents the job-relevant flow in one place:

1. Ask an internal policy question.
2. Review the agent tool trace.
3. Read the citation-backed answer.
4. Inspect evidence chunks.
5. Check evaluation and guardrail metrics.
6. Explain the architecture in four steps.

## Interview Narrative

Use this frontend to tell a concise story:

> This project is not a generic chatbot. It is an enterprise RAG and agent
> workflow demo. The system retrieves policy evidence, builds citation-backed
> answers, exposes tool calls, and runs deterministic evaluation checks so that
> changes can be reviewed rather than trusted blindly.

## Frontend Files

```text
frontend/src/
+-- App.tsx
+-- content.ts
+-- main.tsx
+-- styles.css
```

This is intentionally small. The goal is that the applicant can understand and
explain every React file.

## Screenshot

The canonical screenshot is:

```text
docs/assets/studio/agent-workbench.png
```

Regenerate it with:

```bash
cd frontend
npm run screenshots:studio
```

## Boundaries

- The frontend uses deterministic portfolio demo content.
- It does not replace FastAPI or Streamlit.
- It does not implement real authentication, RBAC, SSO, or production access
  enforcement.
- It does not generate citations in the browser.
- It does not claim production-grade semantic evaluation.
