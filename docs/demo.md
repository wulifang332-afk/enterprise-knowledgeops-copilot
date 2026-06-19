# MVP-0 + Phase 5B Demo Guide

This demo shows a KnowledgeOps workflow, not a chat interface. The purpose is to demonstrate document ingestion, metadata governance, chunk traceability, retrieval scoring, citation inspection, graph inspection, query evidence planning, and optional Phase 5B citation-grounded answer generation.

## Prerequisites

Use Python 3.11 or newer. In this environment, use `python` instead of `python3`.

```bash
cd enterprise-knowledgeops-copilot
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

### 10. Open Knowledge Graph Explorer

Use the Streamlit sidebar to open `Knowledge Graph Explorer`.

This page is for graph inspection only. It does not answer questions and does not perform GraphRAG synthesis.

### 11. Rebuild And Inspect Graph

Click `Rebuild Graph From Processed Chunks`.

Expected result on the current synthetic corpus:

- 96 nodes
- 207 edges
- 40 source chunks

Inspect:

- graph summary metrics
- node table
- edge table
- filters by node type and relation type
- selected node detail
- selected node neighborhood
- evidence quotes for selected edges

Example graph objects:

- `Vendor Payment Request Form`
- `ServiceNow`
- `Severity 1`
- `15 minutes`
- `DPO`
- `Vendor Payment Approval Policy REQUIRES Vendor Payment Request Form`
- `IT Incident Escalation SOP USES_SYSTEM ServiceNow`
- `Severity 1 HAS_TIME_REQUIREMENT 15 minutes`
- `Cross-border Data Handling Policy ESCALATES_TO DPO`

### 12. Open Query Planner

Use the Streamlit sidebar to open `Query Planner`.

This page is for governed query planning, evidence-pack inspection, and optional citation-grounded answer generation. It does not behave like a generic chatbot.

Run these example queries:

```text
Which approval form is required for vendor payments?
What system is used for Severity 1 incidents?
How does cross-border data approval work between APAC and EU?
Show graph evidence around ServiceNow.
What is the capital of France?
```

Expected behavior:

- Enterprise questions return a detected intent, selected route, retrieval evidence, graph evidence, citations, and limitations.
- Out-of-scope questions such as `What is the capital of France?` return a structured refusal.
- Unsupported final-answer requests return a structured refusal.
- With `Generate citation-grounded answer` unchecked, the page preserves Phase 5A evidence-pack behavior.
- With `Generate citation-grounded answer` checked, supported enterprise questions can return an answer, answer citations, and a grounding summary.
- If evidence is insufficient, answer generation is refused instead of fabricating a response.
- The page clearly states that Phase 5B answers are generated only from returned evidence.

Try these answer-generation checks:

```text
Which approval form is required for vendor payments?
What system is used for Severity 1 incidents?
How does cross-border data approval work between APAC and EU?
Tell me the company's travel reimbursement policy for Mars employees.
```

Expected answer-generation behavior:

- Vendor payment answer mentions `Vendor Payment Request Form` and includes answer citations.
- Severity 1 answer mentions `ServiceNow` and includes answer citations.
- Cross-border answer is cautious and cites APAC/EU/Data Protection Officer evidence from the Cross-border Data Handling Policy.
- The Mars employees query is refused as insufficient evidence.

## Optional CLI Demo Check

Run:

```bash
python scripts/demo_mvp0_check.py
```

This verifies the test suite, sample document ingestion, index rebuild, and retrieval evaluation in one command. A successful run ends with:

```text
MVP-0 demo checkpoint passed.
```

To verify Phase 4 graph extraction separately:

```bash
python scripts/rebuild_graph.py
```
