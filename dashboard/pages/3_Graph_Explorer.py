from __future__ import annotations

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.api_client import APIClientError, KnowledgeOpsAPIClient

st.set_page_config(page_title="Graph Explorer", page_icon="GX", layout="wide")
st.title("Knowledge Graph Explorer")
st.caption("Inspectable rule-based enterprise graph. This page does not perform GraphRAG answering.")

client = KnowledgeOpsAPIClient()


def show_api_error(exc: APIClientError) -> None:
    st.error(f"{exc.payload.get('error_code', 'API_ERROR')}: {exc}")
    st.caption(f"request_id: {exc.payload.get('request_id', 'not-issued')}")


if st.button("Rebuild Graph From Processed Chunks", type="primary"):
    with st.spinner("Extracting entities and relations from processed chunks..."):
        try:
            st.session_state["graph_rebuild"] = client.graph_rebuild()
        except APIClientError as exc:
            show_api_error(exc)
            st.stop()

if "graph_rebuild" in st.session_state:
    st.success(
        "Graph rebuilt: "
        f"{st.session_state['graph_rebuild']['node_count']} nodes, "
        f"{st.session_state['graph_rebuild']['edge_count']} edges."
    )

try:
    nodes_response = client.graph_nodes({"limit": 500})
    edges_response = client.graph_edges({"limit": 500})
except APIClientError as exc:
    if exc.payload.get("error_code") == "GRAPH_UNAVAILABLE":
        st.info("No graph artifact is available yet. Rebuild the graph from processed chunks to inspect it here.")
    else:
        show_api_error(exc)
    st.stop()

nodes = nodes_response["items"]
edges = edges_response["items"]
if not nodes:
    st.info("The graph is empty. Rebuild the graph after ingesting documents.")
    st.stop()

node_by_id = {node["node_id"]: node for node in nodes}
node_type_options = sorted({node["type"] for node in nodes})
relation_type_options = sorted({edge["relation_type"] for edge in edges})
source_doc_count = len({doc_id for node in nodes for doc_id in node["source_doc_ids"]})

metrics = st.columns(4)
metrics[0].metric("Nodes", nodes_response["total"])
metrics[1].metric("Edges", edges_response["total"])
metrics[2].metric("Relation Types", len(relation_type_options))
metrics[3].metric("Source Documents", source_doc_count)

with st.sidebar:
    st.subheader("Graph Filters")
    node_type = st.selectbox("Node Type", [""] + node_type_options)
    relation_type = st.selectbox("Relation Type", [""] + relation_type_options)
    label_contains = st.text_input("Node Label Contains")

try:
    filtered_nodes_response = client.graph_nodes(
        {"type": node_type, "label_contains": label_contains, "limit": 500}
    )
    filtered_edges_response = client.graph_edges({"relation_type": relation_type, "limit": 500})
except APIClientError as exc:
    show_api_error(exc)
    st.stop()

filtered_nodes = filtered_nodes_response["items"]
filtered_edges = filtered_edges_response["items"]

st.subheader("Nodes")
node_rows = [
    {
        "node_id": node["node_id"],
        "label": node["label"],
        "type": node["type"],
        "source_docs": len(node["source_doc_ids"]),
        "source_chunks": len(node["source_chunk_ids"]),
        "confidence": node["confidence"],
    }
    for node in filtered_nodes
]
st.dataframe(pd.DataFrame(node_rows), use_container_width=True, hide_index=True)

st.subheader("Edges")
edge_rows = [
    {
        "edge_id": edge["edge_id"],
        "source": node_by_id.get(edge["source_node_id"], {}).get("label", edge["source_node_id"]),
        "relation": edge["relation_type"],
        "target": node_by_id.get(edge["target_node_id"], {}).get("label", edge["target_node_id"]),
        "source_doc_id": edge["source_doc_id"],
        "source_chunk_id": edge["source_chunk_id"],
        "confidence": edge["confidence"],
    }
    for edge in filtered_edges
]
st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)

if not filtered_nodes:
    st.info("No nodes match the current filters.")
    st.stop()

selected_label = st.selectbox(
    "Inspect Node",
    [f"{node['label']} | {node['type']} | {node['node_id']}" for node in filtered_nodes],
)
selected_node_id = selected_label.rsplit(" | ", 1)[-1]
selected_node = next(node for node in filtered_nodes if node["node_id"] == selected_node_id)

left, right = st.columns([1, 1])
with left:
    st.subheader("Selected Node Detail")
    st.json(selected_node, expanded=True)

with right:
    depth = st.slider("Neighborhood Depth", min_value=1, max_value=2, value=1)
    try:
        neighborhood = client.graph_neighborhood(node_id=selected_node_id, depth=depth)
    except APIClientError as exc:
        show_api_error(exc)
        st.stop()
    st.subheader("Neighborhood Summary")
    st.json(
        {
            "node_count": len(neighborhood["nodes"]),
            "edge_count": len(neighborhood["edges"]),
            "depth": neighborhood["depth"],
        },
        expanded=True,
    )

st.subheader("Neighborhood Edges and Evidence")
neighborhood_nodes = {node["node_id"]: node for node in neighborhood["nodes"]}
for edge in neighborhood["edges"]:
    source_label = neighborhood_nodes.get(edge["source_node_id"], {}).get("label", edge["source_node_id"])
    target_label = neighborhood_nodes.get(edge["target_node_id"], {}).get("label", edge["target_node_id"])
    with st.expander(f"{source_label} {edge['relation_type']} {target_label}"):
        st.caption(f"source_doc_id: {edge['source_doc_id']}")
        st.caption(f"source_chunk_id: {edge['source_chunk_id']}")
        st.write(edge["evidence_quote"])
