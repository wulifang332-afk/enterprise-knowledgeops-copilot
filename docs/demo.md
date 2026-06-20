# MVP-0 + Phase 7 Demo Guide

This demo shows a KnowledgeOps workflow, not a chat interface. The purpose is to demonstrate document ingestion, metadata governance, chunk traceability, retrieval scoring, citation inspection, graph inspection, query evidence planning, citation-grounded answers, deterministic quality control, and local feedback governance.

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
- The `Send Feedback for This Result` panel can submit local governance feedback for the latest evidence pack or answer.

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

### 13. Open Evaluation Dashboard

Use the Streamlit sidebar to open `Evaluation Dashboard`.

This page is an internal quality workspace, not a chatbot or production monitoring interface.

Click `Run Evaluation` to execute the versioned `phase6-v1` dataset. The current deterministic baseline should show:

```text
22/22 cases passed
Core: 17/17 passed
Holdout: 5/5 passed
Intent accuracy: 100%
Route accuracy: 100%
Retrieval hit@k: 100%
Citation validity: 100%
Grounded-answer pass rate: 100%
Refusal accuracy: 100%
Fabricated-answer rate: 0%
```

Inspect:

- per-intent metrics
- core versus holdout pass rates
- case-level expected versus actual outcomes
- retrieval and citation results
- graph relations
- generated answers and grounding summaries
- failed checks, when present

Use `Reload Latest` to load the last local report without rerunning the dataset. The dashboard does not implement LLM judging, production monitoring, or online experimentation.

The holdout split uses independently phrased synthetic scenarios to improve regression sensitivity. It is still controlled synthetic evaluation, not proof of broad semantic faithfulness. `N/A` indicates that no applicable cases existed for a metric.

### 14. Open Feedback & Governance

Use the Streamlit sidebar to open `Feedback & Governance`.

This page is a local governance workspace for reviewing quality issues. It is not a production ticketing system or authenticated human workflow tool.

Submit a sample feedback item:

- query/request context: `Which approval form is required for vendor payments?`
- rating: `negative`
- feedback type: `citation_issue`
- issue category: `wrong_citation`
- comment: `Citation should be reviewed before this answer is reused.`

Inspect:

- feedback count by issue category
- feedback count by review status
- negative feedback count
- unresolved feedback count
- review queue table
- selected feedback detail

Use the triage panel to set review status to `triaged`, add a reviewer note, and optionally link a manual evaluation case ID such as `holdout_supplier_invoice_form`.

Expected behavior:

- feedback is stored locally under ignored `data/feedback/` artifacts
- audit events are written under ignored `data/audit/` artifacts
- evaluation datasets are not automatically changed
- no authentication, RBAC, SSO, ticketing integration, LLM judge, monitoring, or online experimentation is involved

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

To run Phase 6 evaluation from the CLI:

```bash
python scripts/run_phase6_eval.py
```
