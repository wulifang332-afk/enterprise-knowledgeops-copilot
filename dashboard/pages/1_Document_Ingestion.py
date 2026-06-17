from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient

st.set_page_config(page_title="Document Ingestion", page_icon="DI", layout="wide")
st.title("Document Ingestion")
st.caption("KnowledgeOps document registry, metadata validation, and chunk inspection.")

client = KnowledgeOpsAPIClient()
raw_files = sorted((PROJECT_ROOT / "data" / "raw").glob("*.md"))

with st.sidebar:
    st.subheader("Raw Source Files")
    if raw_files:
        for file_path in raw_files:
            st.code(file_path.relative_to(PROJECT_ROOT).as_posix())
    else:
        st.warning("No Markdown files found under data/raw/.")

if st.button("Ingest All Documents", type="primary", use_container_width=False):
    with st.spinner("Ingesting documents and rebuilding local retrieval indexes..."):
        try:
            summary = client.ingest_all()
            st.success(
                f"Ingestion complete: {summary['ingested_count']} ingested, "
                f"{summary['skipped_count']} skipped, {summary['failed_count']} failed."
            )
            st.dataframe(pd.DataFrame(summary["results"]), use_container_width=True)
            if summary["index_rebuild"]["attempted"]:
                if summary["index_rebuild"]["succeeded"]:
                    st.info(f"Indexes rebuilt for {summary['index_rebuild']['chunk_count']} chunks.")
                else:
                    st.error(summary["index_rebuild"].get("error") or "Index rebuild failed.")
        except APIClientError as exc:
            payload = exc.payload
            st.error(f"{payload.get('error_code', 'API_ERROR')}: {exc}")
            st.caption(f"request_id: {payload.get('request_id', 'not-issued')}")

st.divider()

try:
    documents_response = client.documents({"limit": 200})
    documents = documents_response["items"]
except APIClientError as exc:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")
    st.stop()

if not documents:
    st.info("No documents are currently ingested. Use the ingestion action above to build the registry.")
    st.stop()

st.subheader("Document Registry")
registry_rows = [
    {
        "doc_id": item["metadata"]["doc_id"],
        "title": item["metadata"]["title"],
        "department": item["metadata"]["department"],
        "regions": ", ".join(item["metadata"]["regions"]),
        "policy_type": item["metadata"]["policy_type"],
        "access_level": item["metadata"]["access_level"],
        "owner": item["metadata"]["owner"],
        "version": item["metadata"]["version"],
        "chunks": item["chunk_count"],
    }
    for item in documents
]
st.dataframe(pd.DataFrame(registry_rows), use_container_width=True, hide_index=True)

selected_doc_id = st.selectbox("Inspect document", [row["doc_id"] for row in registry_rows])
selected_document = next(item for item in documents if item["metadata"]["doc_id"] == selected_doc_id)

left, right = st.columns([1, 2])
with left:
    st.subheader("Metadata")
    st.json(selected_document["metadata"], expanded=True)

with right:
    st.subheader("Chunks")
    try:
        chunks_response = client.chunks({"doc_id": selected_doc_id, "limit": 200})
    except APIClientError as exc:
        st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
        st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")
        st.stop()
    chunk_rows = [
        {
            "chunk_id": chunk["chunk_id"],
            "section_title": chunk["metadata"]["section_title"],
            "token_count": chunk["token_count"],
            "start_char": chunk["start_char"],
            "end_char": chunk["end_char"],
        }
        for chunk in chunks_response["items"]
    ]
    st.dataframe(pd.DataFrame(chunk_rows), use_container_width=True, hide_index=True)
    selected_chunk_id = st.selectbox("Preview chunk", [row["chunk_id"] for row in chunk_rows])
    selected_chunk = next(chunk for chunk in chunks_response["items"] if chunk["chunk_id"] == selected_chunk_id)
    st.text_area("Source chunk text", selected_chunk["text"], height=260)
