export const sampleQuestions = [
  "Can employees paste customer data into public AI tools?",
  "Which approvals are required for an AI tool exception involving personal data?",
  "What should an employee do after accidentally entering prohibited data into an AI tool?"
];

export const toolCalls = [
  {
    name: "search_documents",
    description: "Hybrid retrieval over approved policy and SOP chunks.",
    latency: "1.42s"
  },
  {
    name: "query_with_citations",
    description: "Builds the evidence pack and answer citations.",
    latency: "2.31s"
  },
  {
    name: "inspect_graph",
    description: "Checks related systems, owners, and policy relationships.",
    latency: "0.89s"
  },
  {
    name: "run_evaluation",
    description: "Runs citation, refusal, and retrieval regression checks.",
    latency: "1.10s"
  }
];

export const citationCards = [
  {
    id: "CIT-1",
    title: "Data Security AI Tool Policy v1.0",
    quote:
      "Public AI tools are not approved for company confidential information, customer personal data, employee personal data, source code secrets, or regulated business records.",
    chunk: "chk:data-security-ai-tool-policy:prohibited-data:01",
    hash: "98868ada1c"
  },
  {
    id: "CIT-2",
    title: "AI Tool Exception Process",
    quote:
      "AI tool exceptions require Information Security review. If personal data is involved, the Data Protection Office must also approve the request before use.",
    chunk: "chk:data-security-ai-tool-policy:exception-process:01",
    hash: "1154f3ee18"
  },
  {
    id: "CIT-3",
    title: "Incident Escalation SOP",
    quote:
      "If prohibited data is accidentally entered into an AI tool, the employee must stop using the tool and report the incident to Information Security immediately.",
    chunk: "chk:data-security-ai-tool-policy:incident-response:01",
    hash: "8a4f1220db"
  }
];

export const evaluationRows = [
  { metric: "Retrieval hit@k", score: "20 / 20", status: "Good" },
  { metric: "Citation validity", score: "100%", status: "Passed" },
  { metric: "Refusal behavior", score: "22 / 22", status: "Passed" },
  { metric: "Fabrication rate", score: "0%", status: "Very low" }
];

export const architectureNotes = [
  {
    step: "01",
    title: "Ingest",
    detail: "Validate metadata and create deterministic chunks from synthetic enterprise documents."
  },
  {
    step: "02",
    title: "Retrieve",
    detail: "Combine BM25, vector search, and hybrid ranking into traceable evidence packs."
  },
  {
    step: "03",
    title: "Reason",
    detail: "Route the query, call typed tools, and refuse when evidence is insufficient."
  },
  {
    step: "04",
    title: "Evaluate",
    detail: "Check retrieval hits, citation validity, refusal logic, and feedback governance."
  }
];
