# End-To-End Demo Guide

This guide demonstrates Enterprise KnowledgeOps Copilot as a knowledge operations workflow, not a chat UI. The demo moves from synthetic enterprise documents to retrieval, citations, graph inspection, governed query planning, grounded answers, evaluation, and local feedback governance.

## 1. Install

```bash
cd enterprise-knowledgeops-copilot
python --version
python -m pip install -e ".[dev]"
```

The project runs locally without external API keys.

## 2. Rebuild Retrieval Indexes

```bash
python scripts/rebuild_indexes.py
```

Expected result:

```text
status: success
chunk_count: 40
```

## 3. Rebuild Graph

```bash
python scripts/rebuild_graph.py
```

Expected result:

```text
node_count: 96
edge_count: 207
source_chunk_count: 40
```

## 4. Start FastAPI

```bash
uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

## 5. Start Streamlit

In a second terminal:

```bash
streamlit run dashboard/streamlit_app.py
```

Open:

```text
http://localhost:8501
```

## 6. Ingest And Inspect Documents

Open `Document Ingestion` in Streamlit.

Use the page to:

- view raw Markdown files under `data/raw/`
- click `Ingest All Documents`
- inspect per-file ingestion status
- inspect the document registry
- inspect selected document metadata
- inspect selected chunks, offsets, and source text

Expected clean-run corpus:

```text
8 synthetic enterprise documents
40 processed chunks
0 failed files
```

## 7. Search With Citations

Open `Knowledge Explorer`.

Run these queries in BM25, Vector, and Hybrid modes:

```text
Vendor Payment Request Form
ServiceNow Severity 1 15 minutes
APAC EU cross-border transfer approval
```

Inspect:

- rank
- BM25/vector/hybrid scores
- citation ID
- document ID
- chunk ID
- title and section
- quote
- `start_char` and `end_char`
- `quote_hash`
- source chunk text

The key product point: retrieval results are inspectable and traceable back to source chunks.

## 8. Explore The Knowledge Graph

Open `Knowledge Graph Explorer`.

Click `Rebuild Graph From Processed Chunks` if needed.

Inspect:

- graph summary metrics
- node table
- edge table
- node type filters
- relation type filters
- selected node detail
- selected node neighborhood
- edge evidence quotes

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

The graph is for inspection and evidence enrichment. It is not production GraphRAG answer synthesis.

## 9. Build A Query Planner Evidence Pack

Open `Query Planner`.

Leave `Generate citation-grounded answer` unchecked first.

Run:

```text
Which approval form is required for vendor payments?
```

Inspect:

- detected intent
- selected route
- retrieval evidence
- graph evidence
- citations
- limitations

Expected behavior: the page returns an evidence pack, not a free-form chatbot answer.

## 10. Generate A Citation-Grounded Answer

Check `Generate citation-grounded answer`.

Run:

```text
Which approval form is required for vendor payments?
What system is used for Severity 1 incidents?
How does cross-border data approval work between APAC and EU?
Tell me the company's travel reimbursement policy for Mars employees.
```

Expected behavior:

- vendor payment answer mentions `Vendor Payment Request Form`
- Severity 1 answer mentions `ServiceNow`
- cross-border answer uses APAC/EU/Data Protection Officer evidence
- insufficient-evidence queries are refused instead of fabricated
- answer citations are shown and trace back to evidence-pack citations

Out-of-scope check:

```text
What is the capital of France?
```

Expected behavior:

- `intent=out_of_scope`
- `status=refused`
- no retrieval evidence
- no graph evidence
- no answer

## 11. Run Evaluation

From the CLI:

```bash
python scripts/run_phase6_eval.py
```

Expected current baseline:

```text
Phase 6 evaluation: 22/22 cases passed
Core: 17/17 passed
Holdout: 5/5 passed
Intent accuracy: 100.0%
Route accuracy: 100.0%
Retrieval hit@k: 100.0%
Citation validity: 100.0%
Grounded answer pass: 100.0%
Refusal accuracy: 100.0%
Fabricated answer rate: 0.0%
```

## 12. Inspect Evaluation Dashboard

Open `Evaluation Dashboard`.

Use:

- `Run Evaluation`
- `Reload Latest`
- split metrics for core and holdout
- per-intent breakdown
- case-level expected versus actual outcomes
- failed-case inspection
- limitations section

The evaluation dashboard is deterministic regression inspection, not an LLM judge and not production monitoring.

## 13. Submit Feedback

Use either:

- `Send Feedback for This Result` on the Query Planner page; or
- the submission panel in `Feedback & Governance`.

Example feedback:

```text
query/request context: Which approval form is required for vendor payments?
rating: negative
feedback type: citation_issue
issue category: wrong_citation
comment: Citation should be reviewed before this answer is reused.
linked eval case ID: holdout_supplier_invoice_form
```

Feedback is stored locally under ignored `data/feedback/` artifacts.

## 14. Review Feedback Governance Dashboard

Open `Feedback & Governance`.

Inspect:

- feedback count by issue category
- feedback count by review status
- negative feedback count
- unresolved feedback count
- review queue table
- selected feedback detail
- loaded filter set

Use the triage panel to update:

- review status
- reviewer note
- linked evaluation case ID

Expected behavior:

- local feedback store updates
- local audit events are written under ignored `data/audit/`
- evaluation datasets are not automatically changed
- no authentication, RBAC, SSO, ticketing integration, LLM judge, production monitoring, or online experimentation is involved

## 15. Final Portfolio Check

Run:

```bash
python -m pytest
python scripts/rebuild_indexes.py
python scripts/rebuild_graph.py
python scripts/run_retrieval_eval.py
python scripts/run_phase6_eval.py
python scripts/demo_mvp0_check.py
```

Current expected results:

```text
118 tests passed
retrieval eval: BM25/vector/hybrid all 20/20
graph rebuild: 96 nodes, 207 edges, 40 source chunks
Phase 6 eval: 22/22
MVP-0 demo checkpoint passed
```

## Demo Talk Track

In interviews, frame the project as:

> This is an Enterprise KnowledgeOps platform, not a chatbot. The query interface is one workflow on top of document ingestion, metadata governance, chunk traceability, hybrid retrieval, citation discipline, graph inspection, deterministic evaluation, and local feedback governance.
