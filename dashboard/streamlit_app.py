from __future__ import annotations

from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]

st.set_page_config(
    page_title="Enterprise KnowledgeOps Copilot",
    page_icon="KO",
    layout="wide",
)

st.title("Enterprise KnowledgeOps Copilot")
st.caption("企业知识库自动化构建与 GraphRAG 智能应用平台")

st.markdown(
    """
This Phase 5A build is a KnowledgeOps workspace for document ingestion, metadata review,
chunk inspection, retrieval scoring, citation traceability, graph inspection, and query
planning with evidence packs.
"""
)

col_a, col_b, col_c = st.columns(3)
col_a.metric("Raw Documents", len(list((PROJECT_ROOT / "data" / "raw").glob("*.md"))))
col_b.metric("Processed Documents", len(list((PROJECT_ROOT / "data" / "processed").glob("*.json"))))
col_c.metric("Current Stage", "Phase 5A")

st.subheader("Workflow")
st.write("1. Ingest synthetic enterprise documents.")
st.write("2. Review metadata and generated chunks.")
st.write("3. Search with BM25, vector, or hybrid retrieval.")
st.write("4. Inspect citations, offsets, quote hashes, and source chunks.")
st.write("5. Inspect graph nodes, edges, neighborhoods, and evidence quotes.")
st.write("6. Build query evidence packs with deterministic routing decisions.")

st.info("Phase 5A returns evidence packs only. Final answer generation, GraphRAG synthesis, advanced guardrails, feedback, and full evaluation dashboards are intentionally reserved for later phases.")
