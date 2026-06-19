# Phase 5B API Reference

Base URL:

```text
http://127.0.0.1:8000
```

All Phase 5B responses include `request_id`. Structured errors use:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "Request validation failed.",
  "details": {},
  "request_id": "...",
  "timestamp": "..."
}
```

`/api/v1/query` is available as a governed evidence-pack endpoint. By default it preserves Phase 5A behavior and returns evidence only. When `generate_answer=true`, Phase 5B can add a deterministic citation-grounded answer if the returned evidence is sufficient. It does not call external LLM APIs and does not perform GraphRAG final-response synthesis.

## POST `/api/v1/ingest`

Ingest selected raw files or all files under `data/raw/`. Unsafe paths are rejected by the existing ingestion service.

Selected-file behavior is deterministic:

- If `files` is non-empty, only those files are ingested, even when `ingest_all` is omitted or `true`.
- If `files` is empty and `ingest_all=true`, all raw files are ingested.
- If `files` is empty and `ingest_all=false`, the API returns `INVALID_REQUEST`.
- Selected-file ingestion paths are relative to `data/raw/`. Do not use absolute paths and do not prefix values with `data/raw/`.
- `files` values must resolve under `data/raw/`; traversal paths, absolute paths, paths prefixed with `data/raw/`, symlink escapes, oversized files, and unsupported file types are rejected.

### Request

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

Invalid empty request:

```json
{
  "ingest_all": false,
  "files": []
}
```

Response:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "Provide at least one file or set ingest_all=true.",
  "details": {
    "files": [],
    "ingest_all": false
  },
  "request_id": "...",
  "timestamp": "..."
}
```

### Response Snippet

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

## GET `/api/v1/documents`

Return paginated document summaries.

### Filters

- `department`
- `region`
- `policy_type`
- `access_level`
- `owner`
- `offset`
- `limit`

### Example

```bash
curl 'http://127.0.0.1:8000/api/v1/documents?department=Finance&limit=10'
```

### Response Snippet

```json
{
  "request_id": "...",
  "total": 2,
  "offset": 0,
  "limit": 10,
  "items": [
    {
      "metadata": {
        "doc_id": "vendor-payment-approval-policy-v1-0",
        "title": "Vendor Payment Approval Policy",
        "department": "Finance"
      },
      "section_count": 5,
      "chunk_count": 5
    }
  ]
}
```

## GET `/api/v1/chunks`

Return paginated chunks with metadata and offsets.

### Filters

- `doc_id`
- `section_title`
- `department`
- `region`
- `policy_type`
- `access_level`
- `offset`
- `limit`

### Example

```bash
curl 'http://127.0.0.1:8000/api/v1/chunks?doc_id=vendor-payment-approval-policy-v1-0'
```

### Response Snippet

```json
{
  "request_id": "...",
  "total": 5,
  "items": [
    {
      "chunk_id": "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001",
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "metadata": {
        "section_title": "Required Documents"
      },
      "start_char": 297,
      "end_char": 564,
      "text": "## Required Documents\n\nEvery vendor payment request..."
    }
  ]
}
```

## POST `/api/v1/search`

Search processed chunks using BM25, vector, or hybrid retrieval.

### Request

```json
{
  "query": "Vendor Payment Request Form",
  "retrieval_mode": "hybrid",
  "top_k": 5,
  "filters": {
    "departments": ["Finance"],
    "regions": ["Global"],
    "policy_types": ["policy"]
  }
}
```

`retrieval_mode` values:

- `bm25`
- `vector`
- `hybrid`

### Typed Search Filters

`filters` is a typed object. Extra fields are rejected. Each field must be a list of strings; scalar values such as `"regions": "APAC"` return `INVALID_REQUEST`.

Supported fields:

- `doc_ids`
- `departments`
- `regions`
- `policy_types`
- `owners`
- `access_levels`
- `section_titles`
- `related_processes`

Empty lists are ignored. Valid filters preserve the current behavior: results are restricted before scoring where supported and metadata boosts can still apply in hybrid mode.

Filter values should use canonical lowercase enum values where an enum is involved. Examples include `policy`, `sop`, `internal`, `restricted`, and `confidential`.

Malformed filter example:

```json
{
  "query": "APAC EU cross-border transfer approval",
  "retrieval_mode": "hybrid",
  "top_k": 5,
  "filters": {
    "regions": "APAC"
  }
}
```

Response:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "Request validation failed.",
  "details": {
    "errors": [
      {
        "loc": ["body", "filters", "regions"],
        "msg": "Input should be a valid list"
      }
    ]
  },
  "request_id": "...",
  "timestamp": "..."
}
```

### Response Snippet

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
      "bm25_score": 1.0,
      "vector_score": 0.625195086,
      "hybrid_score": 0.7438572973,
      "citation": {
        "citation_id": "CIT-1",
        "doc_id": "vendor-payment-approval-policy-v1-0",
        "chunk_id": "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001",
        "title": "Vendor Payment Approval Policy",
        "section_title": "Required Documents",
        "source_file": "data/raw/vendor_payment_approval_policy.md",
        "version": "1.0",
        "effective_date": "2025-02-15",
        "start_char": 297,
        "end_char": 564,
        "quote_hash": "368316048cdbc216af0aa95637652453d9a2f12696684a143223988ffdee5fb9"
      }
    }
  ]
}
```

## POST `/api/v1/query`

Classify a question, choose a deterministic evidence route, and return a structured evidence pack. If `generate_answer=true`, the response can also include a citation-grounded answer composed only from returned evidence.

### Request

```json
{
  "query": "Which approval form is required for vendor payments?",
  "top_k": 5,
  "include_graph": true,
  "generate_answer": false,
  "filters": {
    "departments": ["Finance"]
  }
}
```

`filters` uses the same typed search filter object as `/api/v1/search`.

`generate_answer` defaults to `false`. When omitted or false, `/api/v1/query` returns the Phase 5A evidence pack behavior with `answer=null` and `answer_generation_status="not_requested"`.

### Answer Generation Status Values

- `not_requested`
- `generated`
- `refused`
- `insufficient_evidence`

`answer_refusal_reason` can be:

- `OUT_OF_SCOPE`
- `UNSUPPORTED_IN_PHASE_5A`
- `INSUFFICIENT_EVIDENCE`
- `NO_CITABLE_EVIDENCE`
- `null`

### Response Snippet

```json
{
  "request_id": "...",
  "query": "Which approval form is required for vendor payments?",
  "intent": "policy_lookup",
  "route": "hybrid_retrieval_with_policy_filters",
  "status": "evidence_ready",
  "retrieval_evidence": [
    {
      "rank": 1,
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "section_title": "Purpose and Scope",
      "hybrid_score": 0.6794635891,
      "citation": {
        "citation_id": "CIT-1",
        "doc_id": "vendor-payment-approval-policy-v1-0",
        "quote_hash": "48f86308eaad71cf3502199bc7e966431b0a24a588a65f98b02134ce07e27dd7"
      }
    }
  ],
  "graph_evidence": {
    "matched_nodes": [
      {
        "label": "Vendor Payment Request Form",
        "type": "Form"
      }
    ],
    "edges": [
      {
        "relation_type": "REQUIRES",
        "source_doc_id": "vendor-payment-approval-policy-v1-0",
        "source_chunk_id": "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001",
        "evidence_quote": "## Required Documents Every vendor payment request must include a Vendor Payment Request Form..."
      }
    ],
    "relation_types": ["REQUIRES"]
  },
  "citations": [
    {
      "citation_id": "CIT-1",
      "doc_id": "vendor-payment-approval-policy-v1-0"
    }
  ],
  "refusal_reason": null,
  "limitations": [
    "Phase 5B returns citation-grounded answers only when generate_answer=true and evidence is sufficient."
  ],
  "next_phase_note": "Phase 5B can generate citation-grounded answers when generate_answer=true and evidence is sufficient.",
  "answer": null,
  "answer_citations": [],
  "answer_generation_status": "not_requested",
  "answer_refusal_reason": null,
  "grounding_summary": null
}
```

### Citation-Grounded Answer Request

```json
{
  "query": "Which approval form is required for vendor payments?",
  "top_k": 5,
  "include_graph": true,
  "generate_answer": true
}
```

### Citation-Grounded Answer Response Snippet

```json
{
  "request_id": "...",
  "query": "Which approval form is required for vendor payments?",
  "intent": "policy_lookup",
  "route": "hybrid_retrieval_with_policy_filters",
  "status": "evidence_ready",
  "retrieval_evidence": ["..."],
  "graph_evidence": {
    "edges": ["..."]
  },
  "citations": [
    {
      "citation_id": "CIT-4",
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "chunk_id": "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001"
    }
  ],
  "answer": "Vendor payment requests require the Vendor Payment Request Form, plus a valid vendor invoice and either an approved purchase order or an executed contract reference [CIT-4].",
  "answer_citations": [
    {
      "citation_id": "CIT-4",
      "doc_id": "vendor-payment-approval-policy-v1-0",
      "chunk_id": "chk:vendor-payment-approval-policy-v1-0:required-documents:01:353e30e0d4:001"
    }
  ],
  "answer_generation_status": "generated",
  "answer_refusal_reason": null,
  "grounding_summary": "Generated from 1 retrieval citation(s): CIT-4. Source document(s): Vendor Payment Approval Policy. Graph edges considered: 31."
}
```

### Refusal Snippet

```json
{
  "intent": "unsupported",
  "route": "structured_refusal",
  "status": "refused",
  "retrieval_evidence": [],
  "graph_evidence": {
    "matched_nodes": [],
    "neighboring_nodes": [],
    "edges": [],
    "relation_types": []
  },
  "citations": [],
  "refusal_reason": "UNSUPPORTED_IN_PHASE_5A",
  "answer": null,
  "answer_citations": [],
  "answer_generation_status": "refused",
  "answer_refusal_reason": "UNSUPPORTED_IN_PHASE_5A",
  "next_phase_note": "Phase 5B can generate citation-grounded answers when generate_answer=true and evidence is sufficient."
}
```

Out-of-scope questions such as `What is the capital of France?` return `intent="out_of_scope"`, `status="refused"`, no retrieval evidence, no graph evidence, `answer=null`, and `answer_refusal_reason="OUT_OF_SCOPE"` when answer generation is requested.

## POST `/api/v1/graph/rebuild`

Rebuild the deterministic rule-based graph from processed chunks under `data/processed/` and persist the NetworkX graph artifact under `data/graph/`.

This endpoint is for graph inspection setup. It does not answer questions.

### Request

No request body is required.

### Example

```bash
curl -X POST 'http://127.0.0.1:8000/api/v1/graph/rebuild'
```

### Response Snippet

```json
{
  "request_id": "...",
  "node_count": 96,
  "edge_count": 207,
  "source_chunk_count": 40,
  "artifact_path": "/path/to/enterprise-knowledgeops-copilot/data/graph/knowledge_graph.json"
}
```

### Error Behavior

- Returns `INTERNAL_ERROR` if the graph artifact cannot be written.
- Returns structured errors with `request_id` for validation or runtime failures.

## GET `/api/v1/graph/nodes`

Return paginated graph nodes.

### Query Parameters

- `type`: optional exact node type, for example `System`, `Policy`, `Role`, `TimeRequirement`.
- `label_contains`: optional case-insensitive label substring.
- `source_doc_id`: optional document lineage filter.
- `offset`: default `0`.
- `limit`: default `100`, minimum `1`, maximum `500`.

### Example

```bash
curl 'http://127.0.0.1:8000/api/v1/graph/nodes?label_contains=ServiceNow&limit=10'
```

### Response Snippet

```json
{
  "request_id": "...",
  "total": 1,
  "offset": 0,
  "limit": 10,
  "items": [
    {
      "node_id": "node:system:servicenow:bce79939",
      "label": "ServiceNow",
      "type": "System",
      "source_doc_ids": ["it-incident-escalation-sop-v1-0"],
      "source_chunk_ids": [
        "chk:it-incident-escalation-sop-v1-0:purpose-and-scope:01:5a5092dbde:001"
      ],
      "mentions": ["ServiceNow"],
      "confidence": 0.9,
      "created_by": "rule_based_phase4"
    }
  ]
}
```

### Error Behavior

- Returns `GRAPH_UNAVAILABLE` if `data/graph/knowledge_graph.json` does not exist yet.
- Rebuild the graph with `POST /api/v1/graph/rebuild` or `python scripts/rebuild_graph.py`.

## GET `/api/v1/graph/edges`

Return paginated graph edges with source chunk lineage and evidence quotes.

### Query Parameters

- `relation_type`: optional exact relation type, for example `REQUIRES`, `USES_SYSTEM`, `HAS_TIME_REQUIREMENT`, `ESCALATES_TO`.
- `source_doc_id`: optional document lineage filter.
- `source_node_id`: optional exact source node ID.
- `target_node_id`: optional exact target node ID.
- `offset`: default `0`.
- `limit`: default `100`, minimum `1`, maximum `500`.

### Example

```bash
curl 'http://127.0.0.1:8000/api/v1/graph/edges?relation_type=USES_SYSTEM&limit=10'
```

### Response Snippet

```json
{
  "request_id": "...",
  "total": 3,
  "offset": 0,
  "limit": 10,
  "items": [
    {
      "edge_id": "edge:uses-system:56e7625ca37a",
      "source_node_id": "node:sop:it-incident-escalation-sop:249a9a61",
      "target_node_id": "node:system:servicenow:bce79939",
      "relation_type": "USES_SYSTEM",
      "source_doc_id": "it-incident-escalation-sop-v1-0",
      "source_chunk_id": "chk:it-incident-escalation-sop-v1-0:severity-1-workflow:01:557ff9999a:001",
      "evidence_quote": "The IT Service Desk logs the incident in ServiceNow and assigns Severity 1 when the criteria are met.",
      "confidence": 0.85,
      "created_by": "rule_based_phase4"
    }
  ]
}
```

### Error Behavior

- Returns `GRAPH_UNAVAILABLE` if the graph has not been rebuilt.
- Unknown filter values return an empty result set rather than an error.

## GET `/api/v1/graph/neighborhood`

Return a selected node, neighboring nodes, and connecting edges.

### Query Parameters

- `node_id`: required graph node ID.
- `depth`: default `1`, minimum `1`, maximum `2`.

Depth is intentionally capped at `2` to keep the local demo inspectable and prevent large accidental graph traversals.

### Example

```bash
curl 'http://127.0.0.1:8000/api/v1/graph/neighborhood?node_id=node:system:servicenow:bce79939&depth=1'
```

### Response Snippet

```json
{
  "request_id": "...",
  "node_id": "node:system:servicenow:bce79939",
  "depth": 1,
  "selected_node": {
    "node_id": "node:system:servicenow:bce79939",
    "label": "ServiceNow",
    "type": "System",
    "source_doc_ids": ["it-incident-escalation-sop-v1-0"],
    "source_chunk_ids": [
      "chk:it-incident-escalation-sop-v1-0:purpose-and-scope:01:5a5092dbde:001"
    ],
    "mentions": ["ServiceNow"],
    "confidence": 0.9,
    "created_by": "rule_based_phase4"
  },
  "nodes": [],
  "edges": []
}
```

`nodes` and `edges` contain the selected node neighborhood in the real response.

### Error Behavior

- `depth > 2` returns `INVALID_REQUEST` with validation details.
- Unknown `node_id` returns `INVALID_REQUEST`.
- Missing graph artifact returns `GRAPH_UNAVAILABLE`.

## Phase 4 Graph Layer Limitations in the Phase 5B Release

- Graph extraction is deterministic and rule-based.
- Rules are tuned for the synthetic demo corpus.
- This is portfolio/demo information extraction, not production-grade IE.
- Graph endpoints are for inspection, not question answering.
- Neo4j is not implemented in the current Phase 5B release.
