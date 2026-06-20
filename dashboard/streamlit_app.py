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
This Phase 7 build is a KnowledgeOps workspace for document ingestion, metadata review,
chunk inspection, retrieval scoring, citation traceability, graph inspection, and query
planning with evidence packs, optional citation-grounded answers, deterministic quality evaluation,
and local feedback governance.
"""
)

col_a, col_b, col_c = st.columns(3)
col_a.metric("Raw Documents", len(list((PROJECT_ROOT / "data" / "raw").glob("*.md"))))
col_b.metric("Processed Documents", len(list((PROJECT_ROOT / "data" / "processed").glob("*.json"))))
col_c.metric("Current Stage", "Phase 7")

st.subheader("Workflow")
st.write("1. Ingest synthetic enterprise documents.")
st.write("2. Review metadata and generated chunks.")
st.write("3. Search with BM25, vector, or hybrid retrieval.")
st.write("4. Inspect citations, offsets, quote hashes, and source chunks.")
st.write("5. Inspect graph nodes, edges, neighborhoods, and evidence quotes.")
st.write("6. Build query evidence packs with deterministic routing decisions.")
st.write("7. Optionally generate citation-grounded answers from returned evidence.")
st.write("8. Run deterministic regression checks in the Evaluation Dashboard.")
st.write("9. Submit and triage local feedback in the Feedback Governance workspace.")

st.info("Phase 7 adds local feedback governance. It does not add authentication, RBAC, SSO, an LLM judge, production monitoring, Neo4j, or GraphRAG final-response synthesis.")
