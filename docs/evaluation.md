# Evaluation And Governance Reference

The project includes deterministic local evaluation and local feedback governance. Both are designed for portfolio-grade regression inspection, not production validation.

## Evaluation Layers

| Layer | Dataset | Purpose |
|---|---|---|
| Phase 2 retrieval evaluation | `evaluation/datasets/phase2_retrieval_cases.json` | Compare BM25, vector, and hybrid retrieval hit rate |
| Phase 6 query evaluation | `evaluation/datasets/phase6_eval_cases.json` | Check routing, retrieval evidence, citations, answer-grounding rules, and refusals |
| Phase 7 feedback governance | `data/feedback/*.jsonl` local artifacts | Capture human review observations for future manual curation |

No layer uses an external LLM-as-a-judge.

## Phase 2 Retrieval Evaluation

Run:

```bash
python scripts/run_retrieval_eval.py
```

Dataset size:

```text
20 retrieval cases
```

Metric:

```text
hit_rate@5 = cases_with_expected_doc_or_chunk_in_top_5 / total_cases
```

Current deterministic result:

```text
BM25:   20/20, hit_rate@5 = 100%
Vector: 20/20, hit_rate@5 = 100%
Hybrid: 20/20, hit_rate@5 = 100%
```

Interpretation:

- Useful for regression testing exact terms, acronyms, thresholds, systems, form names, and policy names.
- Not a production retrieval accuracy claim.

## Phase 6 Query Evaluation

Run:

```bash
python scripts/run_phase6_eval.py
```

Dataset:

```text
phase6-v1
22 cases total
17 core cases
5 holdout cases
```

The combined dataset covers:

- policy lookup
- process lookup
- fact lookup
- multi-hop routing
- graph exploration
- out-of-scope refusal
- unsupported-request refusal
- insufficient-evidence refusal

The holdout split adds paraphrase, keyword-light, adversarial out-of-scope, and insufficient-evidence cases to improve regression sensitivity. It is intentionally small and does not independently cover every category.

## Phase 6 Metrics

The report includes:

- `intent_accuracy`
- `route_accuracy`
- `retrieval_hit_at_k`
- `retrieval_recall_at_k`
- `expected_chunk_presence_rate`
- `answer_citation_non_empty_rate`
- `citation_validity_rate`
- `expected_citation_match_rate`
- `grounded_answer_pass_rate`
- `refusal_accuracy`
- per-category refusal accuracy
- `fabricated_answer_rate`
- core and holdout pass rates

Unavailable metrics are represented as `null` in JSON and `N/A` in Markdown, CLI output, and Streamlit. Zero-denominator metrics are never rendered as 100%.

Current deterministic result:

```text
Cases passed: 22/22
Core cases: 17/17
Holdout cases: 5/5
Intent accuracy: 100%
Route accuracy: 100%
Retrieval hit@k: 100%
Citation validity: 100%
Grounded-answer pass rate: 100%
Refusal accuracy: 100%
Fabricated-answer rate: 0%
```

## Reports

Generated, ignored artifacts:

```text
data/evaluation/latest_report.json
data/evaluation/latest_report.md
data/evaluation/history/<run_id>.json
```

The JSON report includes run metadata, aggregate metrics, per-intent metrics, confusion summaries, per-case expected and actual outcomes, failed checks, citations, graph relations, and limitations.

## Phase 7 Feedback Governance

Feedback records can be submitted from the Query Planner or Feedback Governance dashboard, or directly through `/api/v1/feedback`.

Feedback stores:

```text
data/feedback/feedback.jsonl
data/feedback/review_queue.json
data/feedback/feedback_corrupt.jsonl
```

These files are ignored by Git. `data/feedback/.gitkeep` is tracked so the directory exists in a clean clone.

Feedback can include manual links to evaluation case IDs. These links are informational only:

- feedback does not automatically add evaluation cases
- feedback does not mutate the dataset
- feedback is not used as an automatic metric source
- feedback can support future manual curation decisions

## Important Interpretation Notes

- The evaluation corpus is synthetic and controlled.
- High metric values are deterministic regression signals, not broad semantic faithfulness proof.
- Citation checks verify structured properties, not full legal or policy correctness.
- Grounding checks verify required phrases, citation subsets, refusal status, and fabricated-answer flags.
- No external LLM judge is implemented.
- No production monitoring or online experimentation is implemented.
- No production human workflow engine is implemented.
- The feedback loop is local JSONL governance demonstration only.
