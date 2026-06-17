# MVP-0 Demo Guide

This demo shows a KnowledgeOps workflow, not a chat interface. The purpose is to demonstrate document ingestion, metadata governance, chunk traceability, retrieval scoring, and citation inspection.

## Prerequisites

Use Python 3.11 or newer. In this environment, use `python` instead of `python3`.

```bash
cd /Users/cube/Documents/Playground/enterprise-knowledgeops-copilot
python --version
```

## Step-by-Step Demo Flow

### 1. Start Backend

```bash
uvicorn backend.main:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

### 2. Start Streamlit

In a second terminal:

```bash
streamlit run dashboard/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

### 3. Open Document Ingestion Page

Use the Streamlit sidebar to open `Document Ingestion`.

This page shows:

- Raw Markdown files under `data/raw/`.
- Ingestion action.
- Per-file ingestion status.
- Document registry table.
- Selected document metadata.
- Selected document chunks.

### 4. Ingest All 8 Documents

Click `Ingest All Documents`.

Expected result:

- 8 documents ingested on a clean run, or 8 skipped if already ingested.
- 0 failed files.
- Index rebuild succeeds.

### 5. Inspect Metadata

Select a document from the registry.

Check fields such as:

- `doc_id`
- `title`
- `department`
- `regions`
- `policy_type`
- `access_level`
- `owner`
- `source_file`
- `content_sha256`

### 6. Inspect Chunks

On the same page, inspect chunk rows.

Check:

- `chunk_id`
- `section_title`
- `token_count`
- `start_char`
- `end_char`
- source chunk text

### 7. Open Knowledge Explorer

Use the Streamlit sidebar to open `Knowledge Explorer`.

This page is for retrieval operations and citation inspection. It is not a chat UI.

### 8. Run Example Queries

Run these queries in BM25, Vector, and Hybrid modes:

```text
Vendor Payment Request Form
ServiceNow Severity 1 15 minutes
APAC EU cross-border transfer approval
```

### 9. Inspect Citations and Source Text

For each result, inspect:

- `citation_id`
- `doc_id`
- `chunk_id`
- `title`
- `section_title`
- `source_file`
- `version`
- `effective_date`
- `quote`
- `start_char`
- `end_char`
- `quote_hash`

The `quote` should match the source chunk text. Offsets and quote hashes provide traceability from search result back to the normalized source document content.

## Optional CLI Demo Check

Run:

```bash
python scripts/demo_mvp0_check.py
```

This verifies the test suite, sample document ingestion, index rebuild, and retrieval evaluation in one command. A successful run ends with:

```text
MVP-0 demo checkpoint passed.
```
