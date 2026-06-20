from __future__ import annotations

from collections import defaultdict

from backend.app.query.schema import AnswerGenerationStatus, EvidencePack, EvidencePackStatus, QueryIntent

from .schema import (
    ActualOutcome,
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationMetrics,
    EvaluationSplit,
    ExpectedOutcome,
    PerIntentMetrics,
    SplitMetrics,
)


def evaluate_case(case: EvaluationCase, pack: EvidencePack) -> EvaluationCaseResult:
    retrieval_doc_ids = ordered_unique(item.doc_id for item in pack.retrieval_evidence)
    chunk_ids = [item.chunk_id for item in pack.retrieval_evidence]
    evidence_citation_ids = [citation.citation_id for citation in pack.citations]
    answer_citation_ids = [citation.citation_id for citation in pack.answer_citations]
    answer_citation_doc_ids = ordered_unique(citation.doc_id for citation in pack.answer_citations)
    graph_relations = sorted({edge.relation_type for edge in pack.graph_evidence.edges}, key=lambda item: item.value)

    expected = ExpectedOutcome(
        intent=case.expected_intent,
        route=case.expected_route,
        status=case.expected_status,
        answer_generation_status=case.expected_answer_generation_status,
        refusal_reason=case.expected_refusal_reason,
        answer_refusal_reason=case.expected_answer_refusal_reason,
        retrieval_doc_ids=case.expected_retrieval_doc_ids,
        chunk_ids=case.expected_chunk_ids,
        citation_doc_ids=case.expected_citation_doc_ids,
        graph_relations=case.expected_graph_relations,
        answer_contains=case.expected_answer_contains,
    )
    actual = ActualOutcome(
        intent=pack.intent,
        route=pack.route,
        status=pack.status,
        answer_generation_status=pack.answer_generation_status,
        refusal_reason=pack.refusal_reason,
        answer_refusal_reason=pack.answer_refusal_reason,
        retrieval_doc_ids=retrieval_doc_ids,
        chunk_ids=chunk_ids,
        evidence_citation_ids=evidence_citation_ids,
        answer_citation_ids=answer_citation_ids,
        answer_citation_doc_ids=answer_citation_doc_ids,
        graph_relations=graph_relations,
        answer=pack.answer,
        grounding_summary=pack.grounding_summary,
    )

    failed_checks: list[str] = []
    check_equal(failed_checks, "intent", case.expected_intent, pack.intent)
    check_equal(failed_checks, "route", case.expected_route, pack.route)
    check_equal(failed_checks, "status", case.expected_status, pack.status)
    check_equal(
        failed_checks,
        "answer_generation_status",
        case.expected_answer_generation_status,
        pack.answer_generation_status,
    )
    check_equal(failed_checks, "refusal_reason", case.expected_refusal_reason, pack.refusal_reason)
    check_equal(
        failed_checks,
        "answer_refusal_reason",
        case.expected_answer_refusal_reason,
        pack.answer_refusal_reason,
    )

    retrieval_hit = None
    retrieval_recall = None
    if case.expected_retrieval_doc_ids:
        expected_docs = set(case.expected_retrieval_doc_ids)
        found_docs = expected_docs.intersection(retrieval_doc_ids)
        retrieval_hit = bool(found_docs)
        retrieval_recall = len(found_docs) / len(expected_docs)
        if not retrieval_hit:
            failed_checks.append("retrieval_expected_document_missing")

    if case.expected_chunk_ids and not set(case.expected_chunk_ids).issubset(chunk_ids):
        failed_checks.append("expected_chunk_missing")

    if case.expected_graph_relations and not set(case.expected_graph_relations).issubset(graph_relations):
        failed_checks.append("expected_graph_relation_missing")

    citation_subset_valid = None
    expected_citation_match = None
    grounding_pass = None
    if case.expected_answer_generation_status == AnswerGenerationStatus.GENERATED:
        citation_subset_valid = bool(answer_citation_ids) and set(answer_citation_ids).issubset(evidence_citation_ids)
        if not citation_subset_valid:
            failed_checks.append("answer_citations_not_valid_subset")

        expected_citation_match = set(case.expected_citation_doc_ids).issubset(answer_citation_doc_ids)
        if not expected_citation_match:
            failed_checks.append("expected_answer_citation_document_missing")

        if not pack.answer:
            failed_checks.append("generated_answer_missing")
        else:
            normalized_answer = pack.answer.casefold()
            for phrase in case.expected_answer_contains:
                if phrase.casefold() not in normalized_answer:
                    failed_checks.append(f"required_answer_phrase_missing:{phrase}")
            for phrase in case.forbidden_answer_contains:
                if phrase.casefold() in normalized_answer:
                    failed_checks.append(f"forbidden_answer_phrase_present:{phrase}")
        if pack.status != EvidencePackStatus.EVIDENCE_READY:
            failed_checks.append("answer_generated_without_evidence_ready")
        if not pack.grounding_summary:
            failed_checks.append("grounding_summary_missing")
        grounding_failures = {
            "answer_citations_not_valid_subset",
            "expected_answer_citation_document_missing",
            "generated_answer_missing",
            "answer_generated_without_evidence_ready",
            "grounding_summary_missing",
        }
        grounding_pass = not any(
            failure in grounding_failures
            or failure.startswith("required_answer_phrase_missing:")
            or failure.startswith("forbidden_answer_phrase_present:")
            for failure in failed_checks
        )
    else:
        if pack.answer is not None:
            failed_checks.append("unexpected_answer_generated")
        if pack.answer_citations:
            failed_checks.append("unexpected_answer_citations")

    is_refusal_case = case.expected_answer_generation_status in {
        AnswerGenerationStatus.REFUSED,
        AnswerGenerationStatus.INSUFFICIENT_EVIDENCE,
    }
    fabricated_answer = is_refusal_case and pack.answer is not None
    refusal_correct = None
    if is_refusal_case:
        refusal_correct = (
            pack.answer is None
            and pack.answer_generation_status == case.expected_answer_generation_status
            and pack.answer_refusal_reason == case.expected_answer_refusal_reason
            and pack.refusal_reason == case.expected_refusal_reason
        )
        if not refusal_correct:
            failed_checks.append("refusal_behavior_incorrect")

    return EvaluationCaseResult(
        case_id=case.case_id,
        split=case.split,
        query=case.query,
        expected=expected,
        actual=actual,
        passed=not failed_checks,
        failed_checks=failed_checks,
        retrieval_hit_at_k=retrieval_hit,
        retrieval_recall_at_k=retrieval_recall,
        citation_subset_valid=citation_subset_valid,
        expected_citation_match=expected_citation_match,
        grounding_pass=grounding_pass,
        refusal_correct=refusal_correct,
        fabricated_answer=fabricated_answer,
    )


def aggregate_metrics(
    cases: list[EvaluationCase], results: list[EvaluationCaseResult]
) -> tuple[EvaluationMetrics, dict[str, PerIntentMetrics], dict[str, dict[str, int]]]:
    total = len(results)
    generated_results = [
        result
        for case, result in zip(cases, results, strict=True)
        if case.expected_answer_generation_status == AnswerGenerationStatus.GENERATED
    ]
    refusal_pairs = [
        (case, result)
        for case, result in zip(cases, results, strict=True)
        if case.expected_answer_generation_status
        in {AnswerGenerationStatus.REFUSED, AnswerGenerationStatus.INSUFFICIENT_EVIDENCE}
    ]
    retrieval_results = [result for result in results if result.retrieval_hit_at_k is not None]
    expected_chunks = sum(len(case.expected_chunk_ids) for case in cases)
    found_chunks = sum(
        len(set(case.expected_chunk_ids).intersection(result.actual.chunk_ids))
        for case, result in zip(cases, results, strict=True)
    )
    total_answer_citations = sum(len(result.actual.answer_citation_ids) for result in generated_results)
    valid_answer_citations = sum(
        len(set(result.actual.answer_citation_ids).intersection(result.actual.evidence_citation_ids))
        for result in generated_results
    )
    expected_citation_docs = sum(len(case.expected_citation_doc_ids) for case in cases)
    matched_citation_docs = sum(
        len(set(case.expected_citation_doc_ids).intersection(result.actual.answer_citation_doc_ids))
        for case, result in zip(cases, results, strict=True)
    )

    metrics = EvaluationMetrics(
        pass_rate=rate(sum(result.passed for result in results), total),
        intent_accuracy=rate(sum(result.expected.intent == result.actual.intent for result in results), total),
        route_accuracy=rate(sum(result.expected.route == result.actual.route for result in results), total),
        retrieval_hit_at_k=rate(sum(bool(result.retrieval_hit_at_k) for result in retrieval_results), len(retrieval_results)),
        retrieval_recall_at_k=average(
            [result.retrieval_recall_at_k for result in retrieval_results if result.retrieval_recall_at_k is not None]
        ),
        expected_chunk_presence_rate=rate(found_chunks, expected_chunks),
        answer_citation_non_empty_rate=rate(
            sum(bool(result.actual.answer_citation_ids) for result in generated_results), len(generated_results)
        ),
        citation_validity_rate=rate(valid_answer_citations, total_answer_citations),
        expected_citation_match_rate=rate(matched_citation_docs, expected_citation_docs),
        grounded_answer_pass_rate=rate(sum(bool(result.grounding_pass) for result in generated_results), len(generated_results)),
        refusal_accuracy=rate(sum(bool(result.refusal_correct) for _, result in refusal_pairs), len(refusal_pairs)),
        out_of_scope_refusal_accuracy=refusal_rate_for_intent(refusal_pairs, QueryIntent.OUT_OF_SCOPE),
        unsupported_refusal_accuracy=refusal_rate_for_intent(refusal_pairs, QueryIntent.UNSUPPORTED),
        insufficient_evidence_refusal_accuracy=rate(
            sum(
                bool(result.refusal_correct)
                for case, result in refusal_pairs
                if case.expected_answer_generation_status == AnswerGenerationStatus.INSUFFICIENT_EVIDENCE
            ),
            sum(
                case.expected_answer_generation_status == AnswerGenerationStatus.INSUFFICIENT_EVIDENCE
                for case, _ in refusal_pairs
            ),
        ),
        fabricated_answer_rate=rate(sum(result.fabricated_answer for _, result in refusal_pairs), len(refusal_pairs)),
    )
    return metrics, per_intent_metrics(cases, results), confusion_summary(results)


def aggregate_split_metrics(
    cases: list[EvaluationCase], results: list[EvaluationCaseResult]
) -> dict[str, SplitMetrics]:
    output: dict[str, SplitMetrics] = {}
    for split in EvaluationSplit:
        selected = [
            result
            for case, result in zip(cases, results, strict=True)
            if case.split == split
        ]
        passed = sum(result.passed for result in selected)
        output[split.value] = SplitMetrics(
            total=len(selected),
            passed=passed,
            failed=len(selected) - passed,
            pass_rate=rate(passed, len(selected)),
        )
    return output


def per_intent_metrics(
    cases: list[EvaluationCase], results: list[EvaluationCaseResult]
) -> dict[str, PerIntentMetrics]:
    grouped: dict[QueryIntent, list[EvaluationCaseResult]] = defaultdict(list)
    for case, result in zip(cases, results, strict=True):
        grouped[case.expected_intent].append(result)
    return {
        intent.value: PerIntentMetrics(
            total=len(intent_results),
            passed=sum(result.passed for result in intent_results),
            pass_rate=rate(sum(result.passed for result in intent_results), len(intent_results)),
            intent_accuracy=rate(
                sum(result.actual.intent == intent for result in intent_results), len(intent_results)
            ),
        )
        for intent, intent_results in sorted(grouped.items(), key=lambda item: item[0].value)
    }


def confusion_summary(results: list[EvaluationCaseResult]) -> dict[str, dict[str, int]]:
    summary: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for result in results:
        summary[result.expected.intent.value][result.actual.intent.value] += 1
    return {
        expected: dict(sorted(actuals.items()))
        for expected, actuals in sorted(summary.items())
    }


def refusal_rate_for_intent(
    pairs: list[tuple[EvaluationCase, EvaluationCaseResult]], intent: QueryIntent
) -> float | None:
    selected = [result for case, result in pairs if case.expected_intent == intent]
    return rate(sum(bool(result.refusal_correct) for result in selected), len(selected))


def check_equal(failures: list[str], name: str, expected, actual) -> None:
    if expected != actual:
        failures.append(f"{name}_mismatch")


def ordered_unique(values) -> list[str]:
    return list(dict.fromkeys(values))


def rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def average(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None
