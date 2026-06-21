import { useEffect, useState } from "react";

import {
  getEvaluationSummary,
  getWorkspaceSummary,
  type EvaluationSummary,
  type WorkspaceSummary
} from "../api";

type SummaryState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const lifecycleSteps = [
  "Documents",
  "Retrieval & Citations",
  "Knowledge Graph",
  "Query Planning",
  "Grounded Answers",
  "Evaluation",
  "Governance"
];

const featureCards = [
  {
    title: "Citation-backed search",
    description: "Inspect retrieved chunks, source files, offsets, and quote hashes."
  },
  {
    title: "Graph inspection",
    description: "Review entities, relationships, neighborhoods, and evidence quotes."
  },
  {
    title: "Governed query routing",
    description: "Turn enterprise questions into routed evidence packs and refusals."
  },
  {
    title: "Quality and feedback loop",
    description: "Track deterministic evaluation outcomes and local governance feedback."
  }
];

export function HomePage() {
  const [workspace, setWorkspace] = useState<SummaryState<WorkspaceSummary>>({
    data: null,
    loading: true,
    error: null
  });
  const [evaluation, setEvaluation] = useState<SummaryState<EvaluationSummary>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let active = true;

    getWorkspaceSummary()
      .then((data) => {
        if (active) {
          setWorkspace({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setWorkspace({ data: null, loading: false, error: messageFor(error) });
        }
      });

    getEvaluationSummary()
      .then((data) => {
        if (active) {
          setEvaluation({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setEvaluation({ data: null, loading: false, error: messageFor(error) });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <section className="hero" aria-labelledby="landing-title">
        <p className="hero__eyebrow">Enterprise KnowledgeOps Copilot</p>
        <h1 className="hero__title" id="landing-title">
          Enterprise KnowledgeOps Studio
        </h1>
        <p className="hero__subtitle">
          A full-stack Enterprise KnowledgeOps prototype for transforming policy, SOP,
          and internal documents into searchable, citation-backed, graph-inspectable,
          answerable, evaluable, and feedback-governed knowledge assets.
        </p>
      </section>

      <section className="section overview" aria-label="Product overview">
        <div className="panel">
          <h2 className="section__title">Product overview</h2>
          <p>
            The Studio is the product-facing workspace for the local-first KnowledgeOps
            platform. It presents the verified ingestion, retrieval, graph, query planning,
            answer grounding, evaluation, and governance chain as a cohesive enterprise
            workflow while Streamlit remains available for technical dashboards.
          </p>
        </div>
        <div className="panel">
          <h2 className="section__title">Local-first posture</h2>
          <p>
            The current build uses local artifacts and deterministic services. It does not
            require authentication, external infrastructure, or hosted LLM evaluation.
          </p>
        </div>
      </section>

      <section className="section" aria-labelledby="lifecycle-title">
        <div className="section__header">
          <h2 className="section__title" id="lifecycle-title">
            KnowledgeOps lifecycle
          </h2>
          <p className="section__note">Documents to governed quality loop</p>
        </div>
        <div className="lifecycle">
          {lifecycleSteps.map((step) => (
            <div className="lifecycle__step" key={step}>
              {step}
            </div>
          ))}
        </div>
      </section>

      <section className="section" aria-labelledby="features-title">
        <div className="section__header">
          <h2 className="section__title" id="features-title">
            Feature cards
          </h2>
        </div>
        <div className="feature-grid">
          {featureCards.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <h3>{feature.title}</h3>
              <p>{feature.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="section" aria-labelledby="metrics-title">
        <div className="section__header">
          <h2 className="section__title" id="metrics-title">
            Workspace summary metrics
          </h2>
          <p className="section__note">Loaded from local FastAPI summary endpoints</p>
        </div>
        <div className="metric-grid">
          <MetricCard label="Documents" state={workspace} value={workspace.data?.documents} />
          <MetricCard label="Chunks" state={workspace} value={workspace.data?.chunks} />
          <MetricCard label="Graph Nodes" state={workspace} value={workspace.data?.graph_nodes} />
          <MetricCard label="Graph Edges" state={workspace} value={workspace.data?.graph_edges} />
          <MetricCard
            label="Evaluation Cases"
            state={evaluation}
            value={evaluation.data?.available ? evaluation.data.total_cases : null}
            unavailableText="No latest report"
          />
          <MetricCard
            label="Passed Cases"
            state={evaluation}
            value={evaluation.data?.available ? evaluation.data.passed_cases : null}
            unavailableText="No latest report"
          />
          <MetricCard
            label="Pass Rate"
            state={evaluation}
            value={
              evaluation.data?.available && evaluation.data.pass_rate !== null
                ? formatPercentage(evaluation.data.pass_rate)
                : null
            }
            unavailableText="No latest report"
          />
          <MetricCard
            label="Fabricated Answer Rate"
            state={evaluation}
            value={
              evaluation.data?.available && evaluation.data.fabricated_answer_rate !== null
                ? formatPercentage(evaluation.data.fabricated_answer_rate)
                : null
            }
            unavailableText="No latest report"
          />
        </div>
      </section>
    </>
  );
}

function MetricCard({
  label,
  state,
  value,
  unavailableText = "Unavailable"
}: {
  label: string;
  state: SummaryState<unknown>;
  value: number | string | null | undefined;
  unavailableText?: string;
}) {
  let content = <span className="metric-card__value">{value ?? unavailableText}</span>;
  let detail = "Local summary";

  if (state.loading) {
    content = <span className="metric-card__value">...</span>;
    detail = "Loading";
  } else if (state.error) {
    content = <span className="metric-card__value">--</span>;
    detail = state.error;
  }

  return (
    <article className="metric-card">
      {content}
      <h3>{label}</h3>
      <p className={state.error ? "status-text status-text--error" : "status-text"}>{detail}</p>
    </article>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "API unavailable";
}

function formatPercentage(value: number): string {
  return `${Math.round(value * 1000) / 10}%`;
}
