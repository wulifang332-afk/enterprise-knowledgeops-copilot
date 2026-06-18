# Phase 3 API Reference

Base URL:

```text
http://127.0.0.1:8000
```

All Phase 3 responses include `request_id`. Structured errors use:

```json
{
  "error_code": "INVALID_REQUEST",
  "message": "Request validation failed.",
  "details": {},
  "request_id": "...",
  "timestamp": "..."
}
```

`/api/v1/query` is intentionally not available until Phase 5, when governed answer generation and GraphRAG are implemented.

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
