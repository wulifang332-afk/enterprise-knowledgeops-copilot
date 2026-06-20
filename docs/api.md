# API Reference

Base URL:

```text
http://127.0.0.1:8000
```

All responses include `request_id`. Structured errors follow this shape:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "Request validation failed.",
  "details": {},
  "request_id": "...",
  "timestamp": "..."
}
```

The API is local-first and demo-oriented. It does not implement production authentication, RBAC, SSO, ticketing workflows, external LLM judging, production monitoring, online experimentation, or Neo4j.

## Ingestion

### `POST /api/v1/ingest`

Purpose: ingest selected files or all files under `data/raw/`, validate metadata, write processed JSON, update the local registry, and optionally rebuild indexes.

Request:

```json
{
  "ingest_all": true,
  "files": null,
  "rebuild_indexes": true
}
```

Selected-file request:

```json
{
  "ingest_all": true,
  "files": ["vendor_payment_approval_policy.md"],
  "rebuild_indexes": true
}
```

Important limitations:

- selected-file paths are relative to `data/raw/`
- absolute paths and `data/raw/`-prefixed paths are rejected
- traversal paths, symlink escapes, oversized files, and unsupported file types are rejected
- only `.md` and `.txt` are accepted in the local demo

Response shape:

Note: evidence and citation arrays are abbreviated in this example. A real generated answer includes retrieval or graph evidence, evidence-pack citations, and non-empty `answer_citations`.

```json
{
  "request_id": "...",
  "total_files": 8,
  "ingested_count": 8,
  "skipped_count": 0,
  "failed_count": 0,
  "results": [
    {
      "source_file": "data/raw/vendor_payment_approval_policy.md",
      "status": "ingested",
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "chunk_count": 5,
      "section_count": 5
    }
  ],
  "index_rebuild": {
    "attempted": true,
    "succeeded": true,
    "chunk_count": 40
  }
}
```

## Documents, Chunks, And Search

### `GET /api/v1/documents`

Purpose: browse paginated document metadata.

Filters:

- `department`
- `region`
- `policy_type`
- `access_level`
- `owner`
- `offset`
- `limit`

Example:

```bash
curl 'http://127.0.0.1:8000/api/v1/documents?department=Finance&limit=10'
```

### `GET /api/v1/chunks`

Purpose: inspect chunk text, metadata, offsets, and source traceability.

Filters:

- `doc_id`
- `section_title`
- `department`
- `region`
- `policy_type`
- `access_level`
- `offset`
- `limit`

Example:

```bash
curl 'http://127.0.0.1:8000/api/v1/chunks?doc_id=vendor-payment-approval-policy-v1-0'
```

### `POST /api/v1/search`

Purpose: search processed chunks with BM25, vector, or hybrid retrieval and return cited chunks.

Request:

```json
{
  "query": "Vendor Payment Request Form",
  "retrieval_mode": "hybrid",
  "top_k": 5,
  "filters": {
    "policy_types": ["policy"],
    "regions": ["Global"]
  }
}
```

Typed filter fields:

- `doc_ids`
- `departments`
- `regions`
- `policy_types`
- `owners`
- `access_levels`
- `section_titles`
- `related_processes`

Response shape:

```json
{
  "request_id": "...",
  "query": "Vendor Payment Request Form",
  "retrieval_mode": "hybrid",
  "top_k": 5,
  "degraded": false,
  "degraded_reasons": [],
  "results": [
    {
      "rank": 1,
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "chunk_id": "chk:...",
      "bm25_score": 1.0,
      "vector_score": 0.87,
      "hybrid_score": 0.94,
      "citation": {
        "citation_id": "CIT-...",
        "doc_id": "vendor-payment-approval-policy-v1-0",
        "chunk_id": "chk:...",
        "title": "Vendor Payment Approval Policy",
        "section_title": "Required Documents",
        "source_file": "data/raw/vendor_payment_approval_policy.md",
        "version": "1.0",
        "effective_date": "2025-01-01",
        "quote": "...",
        "start_char": 0,
        "end_char": 100,
        "quote_hash": "..."
      }
    }
  ]
}
```

Important limitations:

- vector search uses deterministic local mock embeddings
- hybrid scores are designed for the synthetic corpus
- results are retrieval evidence, not final answers

## Graph

### `POST /api/v1/graph/rebuild`

Purpose: rebuild the deterministic rule-based graph from processed chunks.

Example:

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/graph/rebuild'
```

Response shape:

```json
{
  "request_id": "...",
  "node_count": 96,
  "edge_count": 207,
  "source_chunk_count": 40,
  "artifact_path": "/path/to/data/graph/knowledge_graph.json"
}
```

### `GET /api/v1/graph/nodes`

Purpose: list graph nodes.

Filters:

- `type`
- `label_contains`
- `source_doc_id`
- `offset`
- `limit`

Example:

```bash
curl 'http://127.0.0.1:8000/api/v1/graph/nodes?label_contains=ServiceNow'
```

### `GET /api/v1/graph/edges`

Purpose: list graph edges with relation type and evidence quote.

Filters:

- `relation_type`
- `source_doc_id`
- `source_node_id`
- `target_node_id`
- `offset`
- `limit`

Example:

```bash
curl 'http://127.0.0.1:8000/api/v1/graph/edges?relation_type=USES_SYSTEM'
```

### `GET /api/v1/graph/neighborhood`

Purpose: inspect a node neighborhood.

Parameters:

- `node_id`
- `depth`: `1` or `2`

Important limitations:

- graph extraction is rule-based and synthetic-corpus tuned
- graph endpoints are for inspection and evidence enrichment
- Neo4j is not implemented
- graph facts alone are not treated as final answer citations

## Query

### `POST /api/v1/query`

Purpose: classify a question, choose a route, build an evidence pack, and optionally generate a deterministic citation-grounded answer.

Evidence-pack request:

```json
{
  "query": "Which approval form is required for vendor payments?",
  "top_k": 5,
  "include_graph": true,
  "generate_answer": false
}
```

Answer-generation request:

```json
{
  "query": "Which approval form is required for vendor payments?",
  "top_k": 5,
  "include_graph": true,
  "generate_answer": true
}
```

Response shape:

```json
{
  "request_id": "...",
  "query": "Which approval form is required for vendor payments?",
  "intent": "policy_lookup",
  "route": "hybrid_retrieval_with_policy_filters",
  "status": "evidence_ready",
  "retrieval_evidence": ["..."],
  "graph_evidence": {
    "matched_nodes": [],
    "neighboring_nodes": [],
    "edges": [],
    "relation_types": []
  },
  "citations": ["..."],
  "refusal_reason": null,
  "limitations": [],
  "answer": "Vendor payments require the Vendor Payment Request Form.",
  "answer_citations": ["..."],
  "answer_generation_status": "generated",
  "answer_refusal_reason": null,
  "grounding_summary": "Answer composed from returned evidence."
}
```

Out-of-scope behavior:

```json
{
  "query": "What is the capital of France?",
  "intent": "out_of_scope",
  "route": "structured_refusal",
  "status": "refused",
  "retrieval_evidence": [],
  "graph_evidence": {
    "matched_nodes": [],
    "neighboring_nodes": [],
    "edges": [],
    "relation_types": []
  },
  "answer": null,
  "answer_generation_status": "refused",
  "answer_refusal_reason": "OUT_OF_SCOPE"
}
```

Important limitations:

- default behavior is evidence-pack only
- answer generation is deterministic and local
- no external LLM synthesis is required
- no `final_answer` field is used
- unsupported or insufficient-evidence requests are refused

## Evaluation

### `POST /api/v1/evaluation/run`

Purpose: run the deterministic Phase 6 dataset and persist local JSON/Markdown reports.

Response shape:

```json
{
  "request_id": "...",
  "report": {
    "dataset_version": "phase6-v1",
    "total_cases": 22,
    "passed_cases": 22,
    "failed_cases": 0,
    "split_metrics": {
      "core": {
        "total": 17,
        "passed": 17,
        "pass_rate": 1.0
      },
      "holdout": {
        "total": 5,
        "passed": 5,
        "pass_rate": 1.0
      }
    },
    "metrics": {
      "intent_accuracy": 1.0,
      "route_accuracy": 1.0,
      "retrieval_hit_at_k": 1.0,
      "citation_validity_rate": 1.0,
      "grounded_answer_pass_rate": 1.0,
      "refusal_accuracy": 1.0,
      "fabricated_answer_rate": 0.0
    }
  }
}
```

The real response also includes per-intent metrics, confusion summaries, per-case results, failures, and limitations. Some examples are abbreviated for readability.

### `GET /api/v1/evaluation/latest`

Purpose: load the latest local evaluation report.

### `GET /api/v1/evaluation/cases`

Purpose: inspect the versioned evaluation cases.

Important limitations:

- deterministic regression checks only
- no external LLM judge
- no production monitoring
- high scores are not semantic faithfulness proof
- feedback does not automatically mutate evaluation cases

## Feedback

### `POST /api/v1/feedback`

Purpose: submit local governance feedback for answer quality, citations, retrieval, graph evidence, refusals, routing, UI issues, or other observations.

Request:

```json
{
  "query": "Which approval form is required for vendor payments?",
  "request_id": "query-request-id",
  "intent": "policy_lookup",
  "route": "hybrid_retrieval_with_policy_filters",
  "status": "evidence_ready",
  "answer_generation_status": "generated",
  "answer": "Vendor payments require the Vendor Payment Request Form.",
  "citations": [],
  "answer_citations": [],
  "user_rating": "negative",
  "feedback_type": "citation_issue",
  "issue_category": "wrong_citation",
  "comment": "The citation should be reviewed.",
  "linked_eval_case_id": "holdout_supplier_invoice_form",
  "source": "query_planner",
  "metadata": {
    "phase": "7"
  }
}
```

Supported values:

- `user_rating`: `positive`, `negative`, `neutral`
- `feedback_type`: `answer_quality`, `citation_issue`, `retrieval_issue`, `graph_issue`, `refusal_issue`, `routing_issue`, `ui_issue`, `other`
- `issue_category`: `missing_evidence`, `wrong_citation`, `unsupported_answer`, `incorrect_refusal`, `should_have_refused`, `wrong_intent`, `wrong_route`, `irrelevant_graph_context`, `stale_document`, `unclear_answer`, `other`
- `review_status`: `open`, `triaged`, `resolved`, `wont_fix`

Response shape:

```json
{
  "request_id": "...",
  "feedback_id": "fb:...",
  "record": {
    "feedback_id": "fb:...",
    "review_status": "open",
    "user_rating": "negative",
    "feedback_type": "citation_issue",
    "issue_category": "wrong_citation"
  }
}
```

### `GET /api/v1/feedback`

Purpose: list and filter feedback records.

Filters:

- `review_status`
- `feedback_type`
- `issue_category`
- `user_rating`
- `offset`
- `limit`

### `GET /api/v1/feedback/{feedback_id}`

Purpose: read one feedback record.

### `PATCH /api/v1/feedback/{feedback_id}`

Purpose: update local review metadata.

Request:

```json
{
  "review_status": "triaged",
  "reviewer_note": "Candidate for future evaluation curation.",
  "linked_eval_case_id": "holdout_supplier_invoice_form"
}
```

Important limitations:

- feedback is stored locally under ignored `data/feedback/`
- malformed JSONL lines are skipped and quarantined locally
- feedback audit events are local JSONL only
- linked evaluation IDs are manual references
- no production workflow engine, auth, RBAC, SSO, ticketing, monitoring, or online experimentation is implemented
