import { FormEvent, useState } from "react";

import { planQuery, type EvidencePack, type RetrievalEvidenceItem } from "../api";
import {
  AccessPolicySimulationPanel,
  filtersFromAccessPolicy,
  isAccessPolicyBlocked,
  useAccessPolicySimulation,
  type SimulationApplicationStatus
} from "../components/AccessPolicySimulationPanel";

type QueryState = {
  pack: EvidencePack | null;
  loading: boolean;
  error: string | null;
  emptyQuery: boolean;
  hasSubmitted: boolean;
  accessPolicyStatus: SimulationApplicationStatus;
  accessPolicyMessage: string;
};

export function QueryPlannerPage() {
  const [query, setQuery] = useState("");
  const [generateAnswer, setGenerateAnswer] = useState(false);
  const accessPolicy = useAccessPolicySimulation();
  const [state, setState] = useState<QueryState>({
    pack: null,
    loading: false,
    error: null,
    emptyQuery: false,
    hasSubmitted: false,
    accessPolicyStatus: "disabled",
    accessPolicyMessage: "Access policy simulation is disabled. Query requests are unchanged."
  });

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();

    if (trimmedQuery.length < 2) {
      setState({
        pack: null,
        loading: false,
        error: null,
        emptyQuery: true,
        hasSubmitted: true,
        accessPolicyStatus: accessPolicy.enabled ? "ready" : "disabled",
        accessPolicyMessage: accessPolicy.enabled
          ? "Access policy simulation was not run because the query was empty."
          : "Access policy simulation is disabled. Query requests are unchanged."
      });
      return;
    }

    setState({
      pack: null,
      loading: true,
      error: null,
      emptyQuery: false,
      hasSubmitted: true,
      accessPolicyStatus: accessPolicy.enabled ? "ready" : "disabled",
      accessPolicyMessage: accessPolicy.enabled
        ? "Preparing simulation-only filters before query planning."
        : "Access policy simulation is disabled. Query requests are unchanged."
    });

    let filters = {};
    let accessPolicyStatus: SimulationApplicationStatus = "disabled";
    let accessPolicyMessage = "Access policy simulation is disabled. Query requests are unchanged.";

    if (accessPolicy.enabled) {
      const policy = await accessPolicy.runSimulation();
      if (!policy) {
        setState({
          pack: null,
          loading: false,
          error: "Access policy simulation is unavailable. Disable simulation to run default query planning.",
          emptyQuery: false,
          hasSubmitted: true,
          accessPolicyStatus: "unavailable",
          accessPolicyMessage: "No query request was sent because simulation-only filters could not be generated."
        });
        return;
      }
      if (isAccessPolicyBlocked(policy)) {
        setState({
          pack: null,
          loading: false,
          error: null,
          emptyQuery: false,
          hasSubmitted: true,
          accessPolicyStatus: "blocked",
          accessPolicyMessage:
            "No query request was sent because the simulated policy produced no allowed filters."
        });
        return;
      }
      filters = filtersFromAccessPolicy(policy);
      accessPolicyStatus = "applied";
      accessPolicyMessage =
        "Simulation-only allowed_filters were applied to POST /api/v1/query before planning.";
    }

    planQuery(trimmedQuery, generateAnswer, filters)
      .then((pack) => {
        setState({
          pack,
          loading: false,
          error: null,
          emptyQuery: false,
          hasSubmitted: true,
          accessPolicyStatus,
          accessPolicyMessage
        });
      })
      .catch((error: unknown) => {
        setState({
          pack: null,
          loading: false,
          error: messageFor(error),
          emptyQuery: false,
          hasSubmitted: true,
          accessPolicyStatus,
          accessPolicyMessage
        });
      });
  }

  return (
    <>
      <section className="page-heading" aria-labelledby="query-title">
        <p className="hero__eyebrow">Query-routing transparency</p>
        <h1 className="page-heading__title" id="query-title">
          Query Planner
        </h1>
        <p className="page-heading__subtitle">
          Submit an enterprise question and inspect the backend intent, route, evidence
          pack, citations, answer status, and refusal state.
        </p>
      </section>

      <section className="section" aria-labelledby="query-input-title">
        <div className="section__header">
          <h2 className="section__title" id="query-input-title">
            Query Input
          </h2>
          <p className="section__note">POST /api/v1/query, no frontend routing logic</p>
        </div>
        <form className="search-form" onSubmit={handleSubmit}>
          <label className="search-form__label" htmlFor="planner-query">
            Query
          </label>
          <div className="search-form__row">
            <input
              id="planner-query"
              className="search-form__input"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Which approval form is required for vendor payments?"
            />
            <button className="primary-button" type="submit" disabled={state.loading}>
              {state.loading ? "Planning" : "Plan Query"}
            </button>
          </div>
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={generateAnswer}
              onChange={(event) => setGenerateAnswer(event.target.checked)}
            />
            <span>Request backend grounded answer</span>
          </label>
        </form>
      </section>

      <section className="section" aria-labelledby="query-access-policy-title">
        <div className="section__header">
          <h2 className="section__title" id="query-access-policy-title">
            Access Policy Simulation
          </h2>
          <p className="section__note">Optional, simulation-only metadata filters</p>
        </div>
        <AccessPolicySimulationPanel
          controller={accessPolicy}
          applicationStatus={state.accessPolicyStatus}
          appliedDescription={state.accessPolicyMessage}
        />
      </section>

      <QueryOutcome state={state} />
    </>
  );
}

function QueryOutcome({ state }: { state: QueryState }) {
  if (!state.hasSubmitted) {
    return (
      <section className="section">
        <EmptyPanel title="Enter a query" description="Run the planner to inspect an evidence pack." />
      </section>
    );
  }

  if (state.emptyQuery) {
    return (
      <section className="section">
        <EmptyPanel title="Empty query" description="Enter at least two characters to run query planning." />
      </section>
    );
  }

  if (state.loading) {
    return (
      <section className="section">
        <EmptyPanel title="Planning query" description="Calling the local query-planning API." />
      </section>
    );
  }

  if (state.accessPolicyStatus === "blocked") {
    return (
      <section className="section">
        <EmptyPanel
          title="Query blocked by simulation"
          description={state.accessPolicyMessage}
        />
      </section>
    );
  }

  if (state.error) {
    return (
      <section className="section">
        <EmptyPanel title="Query planner unavailable" description={state.error} tone="error" />
      </section>
    );
  }

  if (!state.pack) {
    return (
      <section className="section">
        <EmptyPanel title="No evidence pack" description="The backend did not return a planner response." />
      </section>
    );
  }

  return (
    <>
      <section className="section" aria-labelledby="classification-title">
        <div className="section__header">
          <h2 className="section__title" id="classification-title">
            Query Classification
          </h2>
          <p className="section__note">Backend terminology preserved</p>
        </div>
        <div className="classification-grid">
          <FactCard label="intent" value={state.pack.intent} />
          <FactCard label="route" value={state.pack.route} />
          <FactCard label="status" value={state.pack.status} />
          <FactCard label="answer_generation_status" value={state.pack.answer_generation_status} />
          <FactCard label="refusal_reason" value={state.pack.refusal_reason ?? "null"} />
          <FactCard label="answer_refusal_reason" value={state.pack.answer_refusal_reason ?? "null"} />
        </div>
      </section>

      <section className="section" aria-labelledby="transparency-title">
        <div className="section__header">
          <h2 className="section__title" id="transparency-title">
            Transparency Panel
          </h2>
        </div>
        <div className="metric-grid">
          <MetricTile label="route selected" value={state.pack.route} />
          <MetricTile label="evidence count" value={state.pack.retrieval_evidence.length} />
          <MetricTile label="citation count" value={state.pack.citations.length} />
          <MetricTile label="graph edge count" value={state.pack.graph_evidence.edges.length} />
        </div>
      </section>

      <section className="section" aria-labelledby="answer-title">
        <div className="section__header">
          <h2 className="section__title" id="answer-title">
            Grounded Answer
          </h2>
        </div>
        <AnswerPanel pack={state.pack} />
      </section>

      <section className="section" aria-labelledby="evidence-title">
        <div className="section__header">
          <h2 className="section__title" id="evidence-title">
            Evidence Pack Viewer
          </h2>
          <p className="section__note">Selected evidence, source documents, citations, supporting chunks</p>
        </div>
        <EvidencePackViewer pack={state.pack} />
      </section>
    </>
  );
}

function FactCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="fact-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function MetricTile({ label, value }: { label: string; value: string | number }) {
  return (
    <article className="metric-card">
      <span className="metric-card__value metric-card__value--compact">{value}</span>
      <h3>{label}</h3>
      <p className="status-text">from EvidencePack</p>
    </article>
  );
}

function AnswerPanel({ pack }: { pack: EvidencePack }) {
  if (pack.status === "refused") {
    return (
      <div className="empty-panel empty-panel--error">
        <h3>Refusal state</h3>
        <p>refusal_reason: {pack.refusal_reason ?? "null"}</p>
        <p>answer_refusal_reason: {pack.answer_refusal_reason ?? "null"}</p>
      </div>
    );
  }

  if (pack.answer) {
    return (
      <article className="answer-panel">
        <h3>Backend answer</h3>
        <p>{pack.answer}</p>
        {pack.grounding_summary ? <p className="status-text">{pack.grounding_summary}</p> : null}
      </article>
    );
  }

  return (
    <div className="empty-panel">
      <h3>Evidence-only state</h3>
      <p>answer_generation_status: {pack.answer_generation_status}</p>
      <p>{pack.next_phase_note}</p>
    </div>
  );
}

function EvidencePackViewer({ pack }: { pack: EvidencePack }) {
  if (pack.retrieval_evidence.length === 0 && pack.citations.length === 0 && pack.graph_evidence.edges.length === 0) {
    return (
      <EmptyPanel
        title="No supporting evidence"
        description="The backend returned no retrieval, citation, or graph evidence for this planner response."
      />
    );
  }

  return (
    <div className="evidence-viewer">
      <div className="evidence-column">
        <h3>Selected evidence</h3>
        {pack.retrieval_evidence.length > 0 ? (
          pack.retrieval_evidence.map((item) => <EvidenceItem item={item} key={item.chunk_id} />)
        ) : (
          <p className="status-text">No retrieval_evidence returned.</p>
        )}
      </div>

      <div className="evidence-column">
        <h3>Citations</h3>
        {pack.citations.length > 0 ? (
          pack.citations.map((citation) => (
            <pre className="json-panel" key={citation.citation_id}>
              {JSON.stringify(citation, null, 2)}
            </pre>
          ))
        ) : (
          <p className="status-text">No citations returned.</p>
        )}
      </div>

      <div className="evidence-column evidence-column--wide">
        <h3>Graph evidence</h3>
        <dl className="source-info">
          <div>
            <dt>matched_nodes</dt>
            <dd>{pack.graph_evidence.matched_nodes.length}</dd>
          </div>
          <div>
            <dt>neighboring_nodes</dt>
            <dd>{pack.graph_evidence.neighboring_nodes.length}</dd>
          </div>
          <div>
            <dt>edges</dt>
            <dd>{pack.graph_evidence.edges.length}</dd>
          </div>
          <div>
            <dt>relation_types</dt>
            <dd>{pack.graph_evidence.relation_types.join(", ") || "none"}</dd>
          </div>
        </dl>
        {pack.graph_evidence.edges.slice(0, 5).map((edge) => (
          <pre className="json-panel" key={edge.edge_id}>
            {JSON.stringify(edge, null, 2)}
          </pre>
        ))}
      </div>
    </div>
  );
}

function EvidenceItem({ item }: { item: RetrievalEvidenceItem }) {
  return (
    <article className="evidence-item">
      <div className="result-card__header">
        <div>
          <p className="result-card__rank">Rank {item.rank}</p>
          <h4>{item.title}</h4>
        </div>
        <div className="score-badge">
          <span>{item.hybrid_score.toFixed(3)}</span>
          <small>hybrid_score</small>
        </div>
      </div>
      <dl className="result-meta">
        <div>
          <dt>doc_id</dt>
          <dd>{item.doc_id}</dd>
        </div>
        <div>
          <dt>chunk_id</dt>
          <dd>{item.chunk_id}</dd>
        </div>
        <div>
          <dt>section_title</dt>
          <dd>{item.section_title}</dd>
        </div>
      </dl>
      <details className="result-detail">
        <summary>Inspect supporting chunk</summary>
        <p className="chunk-text">{item.source_text_excerpt}</p>
        <pre className="json-panel">{JSON.stringify(item.citation, null, 2)}</pre>
      </details>
    </article>
  );
}

function EmptyPanel({
  title,
  description,
  tone = "neutral"
}: {
  title: string;
  description: string;
  tone?: "neutral" | "error";
}) {
  return (
    <div className={`empty-panel empty-panel--${tone}`}>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Backend unavailable";
}
