import { useMemo, useState } from "react";

import {
  architectureNotes,
  citationCards,
  evaluationRows,
  sampleQuestions,
  toolCalls
} from "./content";

const navItems = [
  { label: "Ask", icon: "Q" },
  { label: "Evidence", icon: "C" },
  { label: "Evaluation", icon: "E" },
  { label: "Architecture", icon: "A" }
] as const;
type NavItem = (typeof navItems)[number]["label"];

export default function App() {
  const [activeSection, setActiveSection] = useState<NavItem>("Ask");
  const [question, setQuestion] = useState(sampleQuestions[0]);
  const [runCount, setRunCount] = useState(1);

  const traceRows = useMemo(
    () =>
      toolCalls.map((tool, index) => ({
        ...tool,
        runId: `run-${runCount}.${index + 1}`
      })),
    [runCount]
  );

  return (
    <main className="workbench-shell">
      <aside className="sidebar" aria-label="Workbench navigation">
        <div className="brand-block">
          <span className="brand-mark">K</span>
          <div>
            <p className="brand-title">KnowledgeOps</p>
            <p className="brand-subtitle">Agent demo</p>
          </div>
        </div>

        <nav className="nav-list" aria-label="Primary navigation">
          {navItems.map((item) => (
            <button
              className={`nav-button ${activeSection === item.label ? "nav-button--active" : ""}`}
              key={item.label}
              onClick={() => setActiveSection(item.label)}
              type="button"
            >
              <span className="nav-button__icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <strong>Interview focus</strong>
          <span>RAG, tool calls, citations, evals, and governance in one readable screen.</span>
        </div>
      </aside>

      <section className="main-panel">
        <header className="page-header">
          <div>
            <h1>Enterprise KnowledgeOps Agent Workbench</h1>
            <p>
              Ask internal policy questions, inspect the agent plan, review tool calls,
              and verify citation-backed answers before trusting the output.
            </p>
          </div>
          <div className="status-strip" aria-label="System status">
            <span className="status-dot" />
            <span>Agent status: Ready</span>
          </div>
        </header>

        <section className="summary-grid" aria-label="Project highlights">
          <MetricCard label="Retrieval modes" value="3" detail="BM25, vector, hybrid" />
          <MetricCard label="Eval cases" value="22" detail="Core and holdout checks" />
          <MetricCard label="Graph facts" value="207" detail="Inspectable evidence edges" />
          <MetricCard label="Fabrication rate" value="0%" detail="Deterministic baseline" />
        </section>

        <section className="workspace-grid" id="ask">
          <QueryPanel
            question={question}
            onQuestionChange={setQuestion}
            onRun={() => setRunCount((current) => current + 1)}
          />
          <ToolTracePanel rows={traceRows} />
        </section>

        <section className="answer-panel" aria-labelledby="answer-title">
          <div className="section-header">
            <div>
              <h2 id="answer-title">Citation-backed answer</h2>
              <p>Generated from retrieved policy chunks and graph evidence, not unsupported memory.</p>
            </div>
            <span className="quality-badge">Guardrails passed</span>
          </div>
          <p className="answer-copy">
            Public AI tools must not receive customer personal data, employee personal data,
            confidential company information, source code secrets, security credentials, or
            unreleased financial information. Exception requests require Information Security
            review and Data Protection Office approval when personal data is involved.
          </p>
          <CitationList />
        </section>

        <section className="content-grid">
          <EvidenceSection visible={activeSection === "Evidence" || activeSection === "Ask"} />
          <EvaluationSection visible={activeSection === "Evaluation" || activeSection === "Ask"} />
          <ArchitectureSection visible={activeSection === "Architecture"} />
        </section>
      </section>
    </main>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

function QueryPanel({
  question,
  onQuestionChange,
  onRun
}: {
  question: string;
  onQuestionChange: (value: string) => void;
  onRun: () => void;
}) {
  return (
    <section className="panel" aria-labelledby="query-title">
      <div className="panel-header">
        <div>
          <h2 id="query-title">Query</h2>
          <p>Choose a realistic internal knowledge request.</p>
        </div>
      </div>

      <label className="field-label" htmlFor="query-input">
        Internal policy question
      </label>
      <textarea
        id="query-input"
        onChange={(event) => onQuestionChange(event.target.value)}
        value={question}
      />

      <div className="example-list" aria-label="Sample questions">
        {sampleQuestions.map((sample) => (
          <button key={sample} onClick={() => onQuestionChange(sample)} type="button">
            {sample}
          </button>
        ))}
      </div>

      <button className="primary-action" onClick={onRun} type="button">
        <span className="play-icon" aria-hidden="true" />
        Run agent
      </button>
    </section>
  );
}

function ToolTracePanel({ rows }: { rows: Array<(typeof toolCalls)[number] & { runId: string }> }) {
  return (
    <section className="panel" aria-labelledby="trace-title">
      <div className="panel-header">
        <div>
          <h2 id="trace-title">Tool trace</h2>
          <p>Step-by-step tool calls executed by the agent runtime.</p>
        </div>
      </div>
      <div className="trace-list">
        {rows.map((tool, index) => (
          <article className="trace-row" key={tool.runId}>
            <span className="trace-step">{index + 1}</span>
            <div>
              <strong>{tool.name}</strong>
              <p>{tool.description}</p>
            </div>
            <span className="trace-status">Success</span>
            <span className="trace-latency">{tool.latency}</span>
          </article>
        ))}
      </div>
    </section>
  );
}

function CitationList() {
  return (
    <div className="citation-list" aria-label="Citations">
      {citationCards.map((citation) => (
        <article className="citation-chip" key={citation.id}>
          <span>{citation.id}</span>
          <strong>{citation.title}</strong>
        </article>
      ))}
    </div>
  );
}

function EvidenceSection({ visible }: { visible: boolean }) {
  return (
    <section className={`panel evidence-panel ${visible ? "" : "is-muted"}`} aria-labelledby="evidence-title">
      <div className="panel-header">
        <div>
          <h2 id="evidence-title">Evidence</h2>
          <p>Inspectable chunks with offsets and quote hashes.</p>
        </div>
      </div>
      <div className="evidence-list">
        {citationCards.map((citation) => (
          <article className="evidence-card" key={citation.id}>
            <div>
              <span className="small-label">{citation.id}</span>
              <h3>{citation.title}</h3>
            </div>
            <p>{citation.quote}</p>
            <dl>
              <div>
                <dt>Chunk</dt>
                <dd>{citation.chunk}</dd>
              </div>
              <div>
                <dt>Hash</dt>
                <dd>{citation.hash}</dd>
              </div>
            </dl>
          </article>
        ))}
      </div>
    </section>
  );
}

function EvaluationSection({ visible }: { visible: boolean }) {
  return (
    <section className={`panel evaluation-panel ${visible ? "" : "is-muted"}`} aria-labelledby="eval-title">
      <div className="panel-header">
        <div>
          <h2 id="eval-title">Evaluation</h2>
          <p>Deterministic regression checks for answer quality.</p>
        </div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Metric</th>
            <th>Score</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {evaluationRows.map((row) => (
            <tr key={row.metric}>
              <td>{row.metric}</td>
              <td>{row.score}</td>
              <td>
                <span className="table-status">{row.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function ArchitectureSection({ visible }: { visible: boolean }) {
  if (!visible) {
    return null;
  }

  return (
    <section className="panel architecture-panel" aria-labelledby="architecture-title">
      <div className="panel-header">
        <div>
          <h2 id="architecture-title">Architecture</h2>
          <p>The version to explain in interviews.</p>
        </div>
      </div>
      <div className="architecture-flow">
        {architectureNotes.map((item) => (
          <article key={item.title}>
            <span>{item.step}</span>
            <h3>{item.title}</h3>
            <p>{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
