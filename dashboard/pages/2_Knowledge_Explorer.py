from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient

st.set_page_config(page_title="Knowledge Explorer", page_icon="KE", layout="wide")
st.title("Knowledge Explorer")
st.caption("Hybrid enterprise retrieval with score inspection and citation traceability.")

client = KnowledgeOpsAPIClient()

try:
    documents_response = client.documents({"limit": 200})
except APIClientError as exc:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")
    st.stop()

documents = documents_response["items"]
if not documents:
    st.info("No ingested documents are available. Use Document Ingestion first.")
    st.stop()

departments = sorted({item["metadata"]["department"] for item in documents})
regions = sorted({region for item in documents for region in item["metadata"]["regions"]})
policy_types = sorted({item["metadata"]["policy_type"] for item in documents})
access_levels = sorted({item["metadata"]["access_level"] for item in documents})

with st.sidebar:
    st.subheader("Retrieval Controls")
    retrieval_mode = st.radio("Mode", ["hybrid", "bm25", "vector"], format_func=str.upper)
    top_k = st.slider("Top K", min_value=1, max_value=20, value=5)
    department = st.selectbox("Department", [""] + departments)
    region = st.selectbox("Region", [""] + regions)
    policy_type = st.selectbox("Policy Type", [""] + policy_types)
    access_level = st.selectbox("Access Level", [""] + access_levels)

query = st.text_input("Search enterprise knowledge assets", value="vendor payments above USD 50,000 Finance Director CFO")

if st.button("Run Retrieval", type="primary"):
    filters = {
        "departments": [department] if department else [],
        "regions": [region] if region else [],
        "policy_types": [policy_type] if policy_type else [],
        "access_levels": [access_level] if access_level else [],
    }
    payload = {
        "query": query,
        "retrieval_mode": retrieval_mode,
        "top_k": top_k,
        "filters": filters,
    }
    with st.spinner("Searching processed chunks and building citations..."):
        try:
            response = client.search(payload)
        except APIClientError as exc:
            st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
            st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")
            st.stop()

    st.session_state["last_search_response"] = response

response = st.session_state.get("last_search_response")
if not response:
    st.info("Run a retrieval query to inspect scores, citations, and source chunks.")
    st.stop()

st.subheader("Retrieval Results")
if response["degraded"]:
    st.warning("Search ran in degraded mode: " + "; ".join(response["degraded_reasons"]))

results = response["results"]
if not results:
    st.info("No retrieval results matched the query and filters.")
    st.stop()

table_rows = [
    {
        "rank": result["rank"],
        "doc_id": result["doc_id"],
        "section_title": result["metadata"]["section_title"],
        "bm25_score": result["bm25_score"],
        "vector_score": result["vector_score"],
        "hybrid_score": result["hybrid_score"],
        "citation_id": result["citation"]["citation_id"],
    }
    for result in results
]
st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

selected_rank = st.selectbox("Inspect ranked result", [row["rank"] for row in table_rows])
selected = next(result for result in results if result["rank"] == selected_rank)

left, right = st.columns([1, 1])
with left:
    st.subheader("Citation Preview")
    st.json(selected["citation"], expanded=True)

with right:
    st.subheader("Retrieval Metadata")
    st.json(
        {
            "bm25_score": selected["bm25_score"],
            "vector_score": selected["vector_score"],
            "hybrid_score": selected["hybrid_score"],
            "metadata_boost": selected["metadata_boost"],
            "recency_boost": selected["recency_boost"],
        },
        expanded=True,
    )

st.subheader("Source Chunk Text")
st.text_area("Chunk", selected["text"], height=320)

