# Portfolio Summary

## One-Line Summary

Enterprise KnowledgeOps Copilot is a local-first enterprise AI platform that turns synthetic policies and SOPs into searchable, citation-backed, graph-inspectable, query-routable, answerable, evaluable, and feedback-governed knowledge assets.

中文一句话：

面向企业知识库自动化与 GraphRAG-oriented 能力展示的本地优先 portfolio demo：将合成企业文档转化为可检索、可引用、可追溯、可评估、可治理的知识资产。

## Resume Bullet Version

- Built a local-first Enterprise KnowledgeOps Copilot using FastAPI, Streamlit, Pydantic, Chroma, BM25, and NetworkX to transform synthetic enterprise policies/SOPs into governed knowledge assets with ingestion, metadata validation, deterministic chunking, hybrid retrieval, citation traceability, graph inspection, query planning, grounded answers, evaluation, and feedback governance.
- Designed deterministic evaluation and governance workflows: 118 tests, retrieval eval 20/20 across BM25/vector/hybrid, Phase 6 eval 22/22, graph rebuild with 96 nodes and 207 edges from 40 chunks, and clean-clone verification through Phase 7.
- Implemented a product-oriented GenAI workflow that refuses out-of-scope or insufficient-evidence requests and preserves source citations, offsets, hashes, graph evidence, evaluation reports, and local feedback auditability.

中文简历版：

- 构建本地优先的 Enterprise KnowledgeOps Copilot，使用 FastAPI、Streamlit、Pydantic、Chroma、BM25 和 NetworkX，将合成企业政策和 SOP 文档转化为具备元数据治理、确定性切分、混合检索、引用追溯、知识图谱检查、查询规划、引用式回答、评估与反馈治理能力的知识资产平台。
- 设计确定性评估与治理流程：118 个测试通过，BM25/vector/hybrid 检索评估均为 20/20，Phase 6 评估 22/22，知识图谱从 40 个 chunks 构建出 96 个节点和 207 条边，并通过 Phase 7 clean-clone 复现验证。

## LinkedIn Project Version

I built **Enterprise KnowledgeOps Copilot**, a local-first enterprise AI portfolio project focused on knowledge lifecycle management rather than chatbot UX. The platform ingests synthetic enterprise policies and SOPs, validates metadata, creates deterministic chunks, builds BM25/vector/hybrid retrieval indexes, produces traceable citations, extracts a rule-based knowledge graph, routes governed queries, optionally generates citation-grounded answers, evaluates quality with deterministic core/holdout cases, and captures local feedback for governance review.

Current verification: 118 tests, retrieval eval 20/20 across BM25/vector/hybrid, Phase 6 eval 22/22, graph rebuild with 96 nodes and 207 edges from 40 chunks, and clean-clone reproducibility through Phase 7.

中文 LinkedIn 版：

我构建了 **Enterprise KnowledgeOps Copilot**，一个本地优先的企业 AI 作品集项目。它不是通用聊天机器人，而是围绕知识生命周期管理设计：文档接入、元数据治理、确定性 chunk、混合检索、引用追溯、规则型知识图谱、查询规划、引用式回答、确定性评估和本地反馈治理。当前版本通过 118 个测试、检索评估 20/20、Phase 6 评估 22/22，并已完成 Phase 7 clean-clone 复现验证。

## Interview Explanation Version

The core product idea is that enterprise RAG is not just answer generation. A real enterprise knowledge platform needs document operations, metadata quality, chunk traceability, retrieval inspection, source citations, graph evidence, deterministic evaluation, feedback review, and governance boundaries.

I implemented the project phase by phase:

1. Ingestion and metadata validation for 8 synthetic enterprise documents.
2. Deterministic chunking and processed JSON as source of truth.
3. BM25, vector, and hybrid retrieval with citation construction.
4. FastAPI and Streamlit KnowledgeOps dashboard.
5. Rule-based knowledge graph extraction and inspection.
6. Query planning, evidence packs, and deterministic citation-grounded answer generation.
7. Evaluation harness with core and holdout cases.
8. Local feedback and governance review loop.

The project intentionally avoids production claims. It uses a synthetic corpus, deterministic local answer composition, rule-based graph extraction, deterministic evaluation, and JSONL feedback storage. That makes it reproducible and inspectable for portfolio review.

## Technical Highlights

- Local-first FastAPI backend and Streamlit dashboard.
- Pydantic v2 schemas for metadata, retrieval, graph, query, evaluation, and feedback.
- Secure ingestion restricted to `data/raw/`.
- Deterministic chunk IDs using heading occurrence and section path hash.
- BM25 exact-term retrieval plus Chroma vector retrieval with deterministic mock embeddings.
- Hybrid score fusion with citation output.
- Citation fields include document ID, chunk ID, title, section, source file, version, effective date, quote, offsets, and quote hash.
- Rule-based knowledge graph with NetworkX persistence.
- Query router for enterprise intents, graph evidence, retrieval evidence, out-of-scope refusal, and unsupported/insufficient-evidence handling.
- Optional deterministic citation-grounded answer composer.
- Phase 6 evaluation with 17 core and 5 holdout cases.
- Local feedback governance loop with JSONL store, review queue, issue taxonomy, and audit events.

## What I Would Improve Next

- Add optional external LLM provider integration while keeping deterministic mock mode.
- Expand the synthetic corpus and evaluation set.
- Improve entity normalization and relation extraction.
- Add access-control simulation and policy-aware guardrails.
- Add optional Neo4j graph backend.
- Add a real human review workflow integration.
- Add semantic faithfulness evaluation with clear caveats.
- Package deployment only after the local portfolio version remains reproducible.
