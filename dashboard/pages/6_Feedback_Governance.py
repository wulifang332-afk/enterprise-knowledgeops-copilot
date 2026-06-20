from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient
from dashboard.feedback_summary import summarize_feedback

st.set_page_config(page_title="Feedback Governance", page_icon="FG", layout="wide")
st.title("Feedback & Governance")
st.caption(
    "Local KnowledgeOps quality-control workspace for answer quality, citation issues, routing, graph evidence, and refusals."
)

client = KnowledgeOpsAPIClient()

RATINGS = ["positive", "negative", "neutral"]
FEEDBACK_TYPES = [
    "answer_quality",
    "citation_issue",
    "retrieval_issue",
    "graph_issue",
    "refusal_issue",
    "routing_issue",
    "ui_issue",
    "other",
]
ISSUE_CATEGORIES = [
    "missing_evidence",
    "wrong_citation",
    "unsupported_answer",
    "incorrect_refusal",
    "should_have_refused",
    "wrong_intent",
    "wrong_route",
    "irrelevant_graph_context",
    "stale_document",
    "unclear_answer",
    "other",
]
REVIEW_STATUSES = ["open", "triaged", "resolved", "wont_fix"]


def show_api_error(exc: APIClientError) -> None:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")


with st.expander("Submit Feedback", expanded=True):
    st.caption("Feedback is stored locally for demo governance. It does not mutate evaluation datasets automatically.")
    with st.form("feedback_submission_form"):
        query = st.text_input("Query or workflow context", value="")
        request_id = st.text_input("Request ID", value="")
        form_columns = st.columns(4)
        with form_columns[0]:
            user_rating = st.selectbox("Rating", RATINGS, index=1)
        with form_columns[1]:
            feedback_type = st.selectbox("Feedback type", FEEDBACK_TYPES)
        with form_columns[2]:
            issue_category = st.selectbox("Issue category", ISSUE_CATEGORIES)
        with form_columns[3]:
            linked_eval_case_id = st.text_input("Linked eval case ID", value="")
        answer = st.text_area("Answer or evidence context", value="", height=120)
        comment = st.text_area("Reviewer comment", value="", height=120)
        submitted = st.form_submit_button("Submit Feedback", type="primary")
        if submitted:
            payload = {
                "query": query,
                "request_id": request_id or None,
                "answer": answer or None,
                "user_rating": user_rating,
                "feedback_type": feedback_type,
                "issue_category": issue_category,
                "comment": comment,
                "linked_eval_case_id": linked_eval_case_id or None,
                "source": "manual",
            }
            try:
                created = client.feedback_submit(payload)
                st.success(f"Feedback submitted: {created['feedback_id']}")
            except APIClientError as exc:
                show_api_error(exc)

st.subheader("Review Queue")
st.caption("Changing filters refreshes the review queue automatically. Use Reload to re-read the current filter set.")
filter_columns = st.columns(5)
with filter_columns[0]:
    status_filter = st.selectbox("Review status", ["all", *REVIEW_STATUSES])
with filter_columns[1]:
    type_filter = st.selectbox("Feedback type", ["all", *FEEDBACK_TYPES])
with filter_columns[2]:
    category_filter = st.selectbox("Issue category", ["all", *ISSUE_CATEGORIES])
with filter_columns[3]:
    rating_filter = st.selectbox("Rating", ["all", *RATINGS])
with filter_columns[4]:
    reload_clicked = st.button("Reload", use_container_width=True)

params = {
    "review_status": None if status_filter == "all" else status_filter,
    "feedback_type": None if type_filter == "all" else type_filter,
    "issue_category": None if category_filter == "all" else category_filter,
    "user_rating": None if rating_filter == "all" else rating_filter,
    "limit": 500,
}
filter_key = tuple(sorted((key, str(value)) for key, value in params.items()))

if (
    reload_clicked
    or "feedback_records" not in st.session_state
    or st.session_state.get("feedback_filter_key") != filter_key
):
    try:
        response = client.feedback_list(params)
        st.session_state["feedback_records"] = response["items"]
        st.session_state["feedback_summary"] = response["summary"]
        st.session_state["feedback_filter_key"] = filter_key
    except APIClientError as exc:
        show_api_error(exc)
        st.session_state["feedback_records"] = []
        st.session_state["feedback_summary"] = summarize_feedback([])
        st.session_state["feedback_filter_key"] = filter_key

records = st.session_state.get("feedback_records", [])
summary = st.session_state.get("feedback_summary") or summarize_feedback(records)
loaded_filter_text = ", ".join(
    f"{key}={value}" for key, value in params.items() if value not in (None, "", [])
) or "all records"
st.caption(f"Loaded filter set: {loaded_filter_text}")

summary_columns = st.columns(5)
summary_columns[0].metric("Feedback", summary["total_count"])
summary_columns[1].metric("Negative", summary["negative_count"])
summary_columns[2].metric("Unresolved", summary["unresolved_count"])
summary_columns[3].metric("Issue Types", len(summary["by_issue_category"]))
summary_columns[4].metric("Statuses", len(summary["by_review_status"]))

left, right = st.columns([2, 1])
with left:
    if records:
        rows = [
            {
                "feedback_id": record["feedback_id"],
                "rating": record["user_rating"],
                "type": record["feedback_type"],
                "issue": record["issue_category"],
                "status": record["review_status"],
                "linked_eval_case_id": record.get("linked_eval_case_id"),
                "query": record["query"][:120],
            }
            for record in records
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("No feedback records match the current filters.")

with right:
    top_issues = summary.get("top_issue_categories", [])
    if top_issues:
        st.caption("Top Issue Categories")
        st.dataframe(pd.DataFrame(top_issues), use_container_width=True, hide_index=True)
    else:
        st.info("No issue category counts yet.")

if records:
    st.subheader("Triage")
    selected_id = st.selectbox("Select feedback record", [record["feedback_id"] for record in records])
    selected = next(record for record in records if record["feedback_id"] == selected_id)
    detail_left, detail_right = st.columns([1, 1])
    with detail_left:
        st.markdown("**Feedback Detail**")
        st.json(selected, expanded=False)
    with detail_right:
        with st.form("feedback_triage_form"):
            current_status = selected["review_status"]
            next_status = st.selectbox(
                "Review status",
                REVIEW_STATUSES,
                index=REVIEW_STATUSES.index(current_status),
            )
            reviewer_note = st.text_area("Reviewer note", value=selected.get("reviewer_note") or "", height=120)
            linked_eval = st.text_input("Linked eval case ID", value=selected.get("linked_eval_case_id") or "")
            update_clicked = st.form_submit_button("Update Review Status")
            if update_clicked:
                payload = {
                    "review_status": next_status,
                    "reviewer_note": reviewer_note or None,
                    "linked_eval_case_id": linked_eval or None,
                }
                try:
                    updated = client.feedback_update(selected_id, payload)
                    st.success(f"Updated {updated['record']['feedback_id']}")
                    refreshed = client.feedback_list(params)
                    st.session_state["feedback_records"] = refreshed["items"]
                    st.session_state["feedback_summary"] = refreshed["summary"]
                except APIClientError as exc:
                    show_api_error(exc)

with st.expander("Local Governance Boundary"):
    st.write("- Feedback is stored locally under ignored `data/feedback/` artifacts.")
    st.write("- Audit entries are local JSONL events under ignored `data/audit/` artifacts.")
    st.write("- No authentication, RBAC, SSO, ticketing integration, external LLM judge, or monitoring is implemented.")
    st.write("- Linked evaluation case IDs are manual references only; the evaluation dataset is not automatically mutated.")
