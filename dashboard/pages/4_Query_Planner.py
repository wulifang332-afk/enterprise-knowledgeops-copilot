from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient

st.set_page_config(page_title="Query Planner", page_icon="QP", layout="wide")
st.title("Query Planner")
st.caption("Phase 5B can generate citation-grounded answers from returned evidence. Evidence inspection remains visible.")

client = KnowledgeOpsAPIClient()


def show_api_error(exc: APIClientError) -> None:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")


with st.sidebar:
    st.subheader("Planning Controls")
    top_k = st.slider("Top K Retrieval Evidence", min_value=1, max_value=20, value=5)
    include_graph = st.toggle("Include Graph Evidence", value=True)
    generate_answer = st.checkbox("Generate citation-grounded answer", value=False)

query = st.text_input(
    "Enterprise knowledge question",
    value="Which approval form is required for vendor payments?",
)

if st.button("Build Evidence Pack", type="primary"):
    payload = {
        "query": query,
        "top_k": top_k,
        "include_graph": include_graph,
        "generate_answer": generate_answer,
    }
    with st.spinner("Classifying query, selecting route, and collecting evidence..."):
        try:
            st.session_state["last_query_pack"] = client.query(payload)
        except APIClientError as exc:
            show_api_error(exc)
            st.stop()

pack = st.session_state.get("last_query_pack")
if not pack:
    st.info("Build an evidence pack to inspect routing decisions, cited retrieval evidence, and graph evidence.")
    st.stop()

metrics = st.columns(5)
metrics[0].metric("Intent", pack["intent"])
metrics[1].metric("Route", pack["route"])
metrics[2].metric("Status", pack["status"])
metrics[3].metric("Citations", len(pack["citations"]))
metrics[4].metric("Answer", pack["answer_generation_status"])

st.caption(f"request_id: {pack['request_id']}")
st.info(pack["next_phase_note"])
st.caption("Phase 5B answers are generated only from returned evidence. If evidence is insufficient, the system refuses to answer.")

if pack["refusal_reason"]:
    st.warning(f"Refusal reason: {pack['refusal_reason']}")

if pack["limitations"]:
    with st.expander("Limitations and Phase Boundary", expanded=True):
        for item in pack["limitations"]:
            st.write(f"- {item}")

st.subheader("Citation-Grounded Answer")
if pack["answer_generation_status"] == "generated":
    st.success("Answer generated from returned evidence.")
    st.write(pack["answer"])
    if pack["grounding_summary"]:
        st.caption(pack["grounding_summary"])
    answer_citation_rows = [
        {
            "citation_id": citation["citation_id"],
            "doc_id": citation["doc_id"],
            "chunk_id": citation["chunk_id"],
            "title": citation["title"],
            "section_title": citation["section_title"],
        }
        for citation in pack["answer_citations"]
    ]
    if answer_citation_rows:
        st.dataframe(pd.DataFrame(answer_citation_rows), use_container_width=True, hide_index=True)
elif pack["answer_generation_status"] == "not_requested":
    st.info("Answer generation was not requested. Enable the checkbox to request a citation-grounded answer.")
else:
    reason = pack.get("answer_refusal_reason") or pack.get("refusal_reason") or "NOT_GENERATED"
    st.warning(f"Answer not generated: {reason}")
    if pack.get("grounding_summary"):
        st.caption(pack["grounding_summary"])

st.subheader("Retrieval Evidence")
retrieval_rows = [
    {
        "rank": item["rank"],
        "doc_id": item["doc_id"],
        "title": item["title"],
        "section_title": item["section_title"],
        "bm25_score": item["bm25_score"],
        "vector_score": item["vector_score"],
        "hybrid_score": item["hybrid_score"],
        "citation_id": item["citation"]["citation_id"],
    }
    for item in pack["retrieval_evidence"]
]
if retrieval_rows:
    st.dataframe(pd.DataFrame(retrieval_rows), use_container_width=True, hide_index=True)
    selected_rank = st.selectbox("Inspect Retrieval Evidence", [row["rank"] for row in retrieval_rows])
    selected = next(item for item in pack["retrieval_evidence"] if item["rank"] == selected_rank)
    left, right = st.columns([1, 1])
    with left:
        st.subheader("Citation")
        st.json(selected["citation"], expanded=True)
    with right:
        st.subheader("Source Metadata")
        st.json(selected["source_document_metadata"], expanded=False)
    st.text_area("Source Chunk Excerpt", selected["source_text_excerpt"], height=260)
else:
    st.info("No retrieval evidence was returned for this route.")

st.subheader("Graph Evidence")
graph = pack["graph_evidence"]
graph_nodes = graph["neighboring_nodes"]
graph_edges = graph["edges"]
node_by_id = {node["node_id"]: node for node in graph_nodes}

node_rows = [
    {
        "node_id": node["node_id"],
        "label": node["label"],
        "type": node["type"],
        "source_docs": len(node["source_doc_ids"]),
        "source_chunks": len(node["source_chunk_ids"]),
    }
    for node in graph_nodes
]
edge_rows = [
    {
        "source": node_by_id.get(edge["source_node_id"], {}).get("label", edge["source_node_id"]),
        "relation": edge["relation_type"],
        "target": node_by_id.get(edge["target_node_id"], {}).get("label", edge["target_node_id"]),
        "source_doc_id": edge["source_doc_id"],
        "source_chunk_id": edge["source_chunk_id"],
    }
    for edge in graph_edges
]

left, right = st.columns([1, 1])
with left:
    st.caption("Matched Nodes")
    st.json(graph["matched_nodes"], expanded=False)
    st.caption("Neighboring Nodes")
    if node_rows:
        st.dataframe(pd.DataFrame(node_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No graph nodes were returned.")

with right:
    st.caption("Edges")
    if edge_rows:
        st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)
        st.caption("Relation types: " + ", ".join(graph["relation_types"]))
    else:
        st.info("No graph edges were returned.")

if graph_edges:
    st.subheader("Graph Evidence Quotes")
    for edge in graph_edges[:10]:
        source = node_by_id.get(edge["source_node_id"], {}).get("label", edge["source_node_id"])
        target = node_by_id.get(edge["target_node_id"], {}).get("label", edge["target_node_id"])
        with st.expander(f"{source} {edge['relation_type']} {target}"):
            st.caption(f"source_doc_id: {edge['source_doc_id']}")
            st.caption(f"source_chunk_id: {edge['source_chunk_id']}")
            st.write(edge["evidence_quote"])
