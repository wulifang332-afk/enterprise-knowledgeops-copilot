from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient
from dashboard.evaluation_formatting import format_percentage

st.set_page_config(page_title="Evaluation Dashboard", page_icon="EV", layout="wide")
st.title("Evaluation Dashboard")
st.caption("Deterministic KnowledgeOps quality inspection for retrieval, routing, citations, grounding, and refusals.")

client = KnowledgeOpsAPIClient(timeout_seconds=120.0)


def show_api_error(exc: APIClientError) -> None:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")


run_column, reload_column, note_column = st.columns([1, 1, 4])
with run_column:
    run_clicked = st.button("Run Evaluation", type="primary", use_container_width=True)
with reload_column:
    reload_clicked = st.button("Reload Latest", use_container_width=True)
with note_column:
    st.info("Local deterministic checks only. No LLM judge, feedback collection, or production monitoring.")

if run_clicked:
    with st.spinner("Running deterministic Phase 6 evaluation..."):
        try:
            st.session_state["phase6_report"] = client.evaluation_run()["report"]
        except APIClientError as exc:
            show_api_error(exc)
elif reload_clicked:
    with st.spinner("Loading latest evaluation report..."):
        try:
            st.session_state["phase6_report"] = client.evaluation_latest()["report"]
        except APIClientError as exc:
            show_api_error(exc)

report = st.session_state.get("phase6_report")
if report:
    st.subheader("Overview")
    overview = st.columns(5)
    overview[0].metric("Total Cases", report["total_cases"])
    overview[1].metric("Passed", report["passed_cases"])
    overview[2].metric("Failed", report["failed_cases"])
    overview[3].metric("Dataset", report["dataset_version"])
    overview[4].metric("Run", report["run_id"])
    st.caption(f"Evaluation timestamp: {report['timestamp']}")
    split_columns = st.columns(4)
    split_columns[0].metric("Core Cases", report["split_metrics"]["core"]["total"])
    split_columns[1].metric("Core Pass Rate", format_percentage(report["split_metrics"]["core"]["pass_rate"]))
    split_columns[2].metric("Holdout Cases", report["split_metrics"]["holdout"]["total"])
    split_columns[3].metric(
        "Holdout Pass Rate", format_percentage(report["split_metrics"]["holdout"]["pass_rate"])
    )

    metrics = report["metrics"]
    st.subheader("Quality Metrics")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Intent Accuracy", format_percentage(metrics["intent_accuracy"]))
    metric_columns[1].metric("Route Accuracy", format_percentage(metrics["route_accuracy"]))
    metric_columns[2].metric("Retrieval Hit@K", format_percentage(metrics["retrieval_hit_at_k"]))
    metric_columns[3].metric("Citation Validity", format_percentage(metrics["citation_validity_rate"]))
    metric_columns = st.columns(4)
    metric_columns[0].metric("Grounded Answers", format_percentage(metrics["grounded_answer_pass_rate"]))
    metric_columns[1].metric("Refusal Accuracy", format_percentage(metrics["refusal_accuracy"]))
    metric_columns[2].metric("Expected Citations", format_percentage(metrics["expected_citation_match_rate"]))
    metric_columns[3].metric("Fabricated Answers", format_percentage(metrics["fabricated_answer_rate"]))

    st.subheader("Per-Intent Breakdown")
    intent_rows = [
        {
            "intent": intent,
            "total": values["total"],
            "passed": values["passed"],
            "pass_rate": values["pass_rate"],
            "intent_accuracy": values["intent_accuracy"],
        }
        for intent, values in report["per_intent_metrics"].items()
    ]
    st.dataframe(pd.DataFrame(intent_rows), use_container_width=True, hide_index=True)

    st.subheader("Case Results")
    all_results = report["per_case_results"]
    intents = sorted({item["expected"]["intent"] for item in all_results})
    filter_columns = st.columns(3)
    with filter_columns[0]:
        intent_filter = st.selectbox("Expected intent", ["all", *intents])
    with filter_columns[1]:
        split_filter = st.selectbox("Dataset split", ["all", "core", "holdout"])
    with filter_columns[2]:
        result_filter = st.selectbox("Result", ["all", "passed", "failed"])

    filtered_results = [
        item
        for item in all_results
        if (intent_filter == "all" or item["expected"]["intent"] == intent_filter)
        and (split_filter == "all" or item["split"] == split_filter)
        and (
            result_filter == "all"
            or (result_filter == "passed" and item["passed"])
            or (result_filter == "failed" and not item["passed"])
        )
    ]
    case_rows = [
        {
            "case_id": item["case_id"],
            "split": item["split"],
            "passed": item["passed"],
            "expected_intent": item["expected"]["intent"],
            "actual_intent": item["actual"]["intent"],
            "route": item["actual"]["route"],
            "answer_status": item["actual"]["answer_generation_status"],
            "retrieval_hit": item["retrieval_hit_at_k"],
            "failed_checks": ", ".join(item["failed_checks"]),
        }
        for item in filtered_results
    ]
    st.dataframe(pd.DataFrame(case_rows), use_container_width=True, hide_index=True)

    if filtered_results:
        selected_id = st.selectbox("Inspect Case", [item["case_id"] for item in filtered_results])
        selected = next(item for item in filtered_results if item["case_id"] == selected_id)
        st.caption(selected["query"])
        expected_column, actual_column = st.columns(2)
        with expected_column:
            st.markdown("**Expected Outcome**")
            st.json(selected["expected"], expanded=True)
        with actual_column:
            st.markdown("**Actual Outcome**")
            st.json(selected["actual"], expanded=True)
        if selected["actual"].get("answer"):
            st.markdown("**Generated Answer**")
            st.write(selected["actual"]["answer"])
            st.caption(selected["actual"].get("grounding_summary") or "No grounding summary")
        if selected["failed_checks"]:
            st.error("Failed checks: " + ", ".join(selected["failed_checks"]))

    if report["failures"]:
        st.subheader("Failed Case Details")
        for failure in report["failures"]:
            with st.expander(failure["case_id"]):
                st.write(failure["query"])
                st.write(failure["failed_checks"])

    with st.expander("Evaluation Limitations"):
        for limitation in report["limitations"]:
            st.write(f"- {limitation}")
else:
    st.info("Run the Phase 6 evaluation or reload the latest report to inspect quality metrics.")
