# Evaluation Reference

The project has two deterministic local evaluation layers:

- Phase 2 retrieval evaluation compares BM25, vector, and hybrid retrieval.
- Phase 6 evaluation checks retrieval, routing, citations, answer-grounding rules, and refusal behavior across canonical enterprise scenarios.

Neither layer uses an LLM-as-a-judge. Deterministic citation checks are not equivalent to semantic answer faithfulness.

## Phase 2 Retrieval Dataset

Dataset file:

```text
evaluation/datasets/phase2_retrieval_cases.json
```

Dataset size:

```text
20 retrieval cases
```

The cases are synthetic and tied to deterministic Phase 1 chunk IDs. They cover exact terms, policy names, form names, systems, thresholds, acronyms, and region names.

## Phase 2 Metrics

### hit_rate@5

A retrieval case is counted as a hit if at least one expected chunk ID or expected document ID appears in the top 5 results.

```text
hit_rate@5 = cases_with_hit_in_top_5 / total_cases
```

### Baseline Comparison

The script compares:

- BM25 retrieval
- Vector retrieval
- Hybrid retrieval

The acceptance rule is:

```text
hybrid hit_rate@5 >= BM25 hit_rate@5
hybrid hit_rate@5 >= vector hit_rate@5
hybrid hit_rate@5 >= 80%
```

## Phase 2 Current Result

Latest run:

```text
BM25:   20/20, hit_rate@5 = 100%
Vector: 20/20, hit_rate@5 = 100%
Hybrid: 20/20, hit_rate@5 = 100%
```

Hybrid is not below the BM25 or vector baselines on this dataset.

## Phase 2 Run Command

```bash
python scripts/run_retrieval_eval.py
```

## Phase 6 Evaluation Dataset

Dataset file:

```text
evaluation/datasets/phase6_eval_cases.json
```

The versioned `phase6-v1` dataset contains 22 deterministic cases: 17 core regression cases and 5 independently phrased holdout cases. The combined Phase 6 dataset covers:

- policy lookup
- process lookup
- fact lookup
- multi-hop routing
- graph exploration
- out-of-scope refusal
- unsupported-request refusal
- insufficient-evidence refusal

Each case declares expected intent, route, status, retrieval documents or chunks where applicable, graph relations, answer phrases, citations, and refusal outcomes.

The holdout split adds paraphrase, keyword-light, adversarial out-of-scope, and insufficient-evidence cases to improve regression sensitivity. It is intentionally small and does not independently cover every category. The holdout cases remain grounded in or intentionally rejected against the same controlled synthetic corpus.

## Phase 6 Metrics

The Phase 6 report includes:

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
- core and holdout case totals and pass rates

Grounding checks verify deterministic properties only: answers are generated only from evidence-ready packs, required phrases are present, forbidden known phrases are absent, answer citations are a subset of evidence-pack citations, expected citation documents are present, and a grounding summary exists.

When no applicable cases exist for a metric, its value is `null` in JSON and `N/A` in Markdown, CLI, and Streamlit. A zero denominator is never rendered as 100%.

## Phase 6 Reports

Run:

```bash
python scripts/run_phase6_eval.py
```

Generated, ignored artifacts:

```text
data/evaluation/latest_report.json
data/evaluation/latest_report.md
data/evaluation/history/<run_id>.json
```

The JSON report includes run metadata, aggregate metrics, per-intent metrics, an intent confusion summary, per-case expected and actual outcomes, failed checks, citations, graph relations, and limitations.

The command exits non-zero for execution errors. Metric degradation is reported without failing the command unless `--fail-on-regression` is supplied.

## Phase 6 Current Result

Latest deterministic run:

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

## Important Interpretation Note

This is a controlled synthetic evaluation. The 100% score is useful for regression testing and demonstrating that the MVP-0 retrieval pipeline works on the sample corpus.

It is not a production validation claim and should not be interpreted as expected performance on real enterprise documents. Phase 6 does not measure free-form semantic correctness, complete policy interpretation, or production safety. No human feedback loop, production monitoring, online experimentation, or external evaluator is implemented.
