# Phase 2 Retrieval Evaluation

This document covers only the current retrieval evaluation implemented before MVP-0 stabilization.

It does not evaluate answer generation, GraphRAG, guardrails, feedback, or full end-to-end RAG quality. Those capabilities are not implemented yet.

## Dataset

Dataset file:

```text
evaluation/datasets/phase2_retrieval_cases.json
```

Dataset size:

```text
20 retrieval cases
```

The cases are synthetic and tied to deterministic Phase 1 chunk IDs. They cover exact terms, policy names, form names, systems, thresholds, acronyms, and region names.

## Metrics

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

## Current Result

Latest run:

```text
BM25:   20/20, hit_rate@5 = 100%
Vector: 20/20, hit_rate@5 = 100%
Hybrid: 20/20, hit_rate@5 = 100%
```

Hybrid is not below the BM25 or vector baselines on this dataset.

## Run Command

```bash
python scripts/run_retrieval_eval.py
```

## Important Interpretation Note

This is a controlled synthetic evaluation. The 100% score is useful for regression testing and demonstrating that the MVP-0 retrieval pipeline works on the sample corpus.

It is not a production validation claim and should not be interpreted as expected performance on real enterprise documents.
