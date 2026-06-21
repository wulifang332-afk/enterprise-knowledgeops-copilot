import { useEffect, useMemo, useState } from "react";

import {
  getReadinessPersonas,
  getReadinessSummary,
  simulateAccessPolicy,
  type AccessLevel,
  type AccessPolicyResponse,
  type CorpusMetadataDistributions,
  type PersonaListResponse,
  type PolicyType,
  type ReadinessSummary
} from "../api";

type LoadState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const samplePolicyRequest = {
  requested_departments: ["Finance", "Human Resources"],
  requested_regions: ["APAC", "EU"],
  requested_policy_types: ["policy", "manual"] as PolicyType[],
  requested_access_levels: ["internal", "confidential"] as AccessLevel[],
  requested_owners: ["Finance Operations", "Data Protection Office"]
};

export function ReadinessCenterPage() {
  const [summary, setSummary] = useState<LoadState<ReadinessSummary>>({
    data: null,
    loading: true,
    error: null
  });
  const [personas, setPersonas] = useState<LoadState<PersonaListResponse>>({
    data: null,
    loading: true,
    error: null
  });
  const [selectedPersonaId, setSelectedPersonaId] = useState("finance_manager_apac");
  const [policy, setPolicy] = useState<LoadState<AccessPolicyResponse>>({
    data: null,
    loading: false,
    error: null
  });

  useEffect(() => {
    let active = true;

    getReadinessSummary()
      .then((data) => {
        if (active) {
          setSummary({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setSummary({ data: null, loading: false, error: messageFor(error) });
        }
      });

    getReadinessPersonas()
      .then((data) => {
        if (!active) {
          return;
        }
        setPersonas({ data, loading: false, error: null });
        if (!data.items.some((persona) => persona.persona_id === selectedPersonaId) && data.items[0]) {
          setSelectedPersonaId(data.items[0].persona_id);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setPersonas({ data: null, loading: false, error: messageFor(error) });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const selectedPersona = useMemo(
    () => personas.data?.items.find((persona) => persona.persona_id === selectedPersonaId) ?? null,
    [personas.data, selectedPersonaId]
  );

  useEffect(() => {
    if (!personas.data?.items.length || !selectedPersonaId) {
      return;
    }
    runSimulation();
  }, [personas.data, selectedPersonaId]);

  function runSimulation() {
    if (!selectedPersonaId) {
      return;
    }
    setPolicy({ data: null, loading: true, error: null });
    simulateAccessPolicy({
      persona_id: selectedPersonaId,
      ...samplePolicyRequest
    })
      .then((data) => setPolicy({ data, loading: false, error: null }))
      .catch((error: unknown) => setPolicy({ data: null, loading: false, error: messageFor(error) }));
  }

  return (
    <>
      <section className="page-heading" aria-labelledby="readiness-title">
        <p className="hero__eyebrow">Enterprise readiness simulation</p>
        <h1 className="page-heading__title" id="readiness-title">
          Readiness Center
        </h1>
        <p className="page-heading__subtitle">
          Read-only visibility into local access-policy simulation, metadata filter generation,
          corpus readiness, evaluation status, and governance status.
        </p>
      </section>

      <section className="section" aria-labelledby="readiness-overview-title">
        <div className="section__header">
          <h2 className="section__title" id="readiness-overview-title">
            Readiness Summary
          </h2>
          <p className="section__note">GET /api/v1/readiness/summary</p>
        </div>
        <div className="metric-grid">
          <ReadinessMetric label="personas_count" value={summary.data?.personas_count} state={summary} />
          <ReadinessMetric
            label="access_levels"
            value={summary.data?.access_levels.length}
            state={summary}
          />
          <ReadinessMetric
            label="graph_nodes"
            value={summary.data?.graph_status.node_count}
            state={summary}
            detail={summary.data?.graph_status.available ? "graph artifact available" : "graph artifact unavailable"}
          />
          <ReadinessMetric
            label="feedback_count"
            value={summary.data?.governance_status.feedback_count}
            state={summary}
            detail={summary.data?.governance_status.available ? "feedback artifact available" : "feedback artifact unavailable"}
          />
        </div>
        {summary.error ? (
          <div className="inline-alert readiness-alert">GET /api/v1/readiness/summary: {summary.error}</div>
        ) : null}
      </section>

      <section className="section" aria-labelledby="boundary-title">
        <div className="section__header">
          <h2 className="section__title" id="boundary-title">
            Simulation Boundary
          </h2>
          <p className="section__note">local-first, read-only, not authorization</p>
        </div>
        <div className="overview">
          <div className="panel">
            <h3>readiness_capabilities</h3>
            {summary.data ? (
              <pre className="json-panel">{JSON.stringify(summary.data.readiness_capabilities, null, 2)}</pre>
            ) : (
              <p className="status-text">Capability summary unavailable.</p>
            )}
          </div>
          <div className="panel">
            <h3>non_goals</h3>
            {summary.data ? (
              <ul className="boundary-list">
                {summary.data.non_goals.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="status-text">Boundary list unavailable.</p>
            )}
          </div>
        </div>
      </section>

      <section className="section" aria-labelledby="personas-title">
        <div className="section__header">
          <h2 className="section__title" id="personas-title">
            Simulated Personas
          </h2>
          <p className="section__note">GET /api/v1/readiness/personas</p>
        </div>
        <PersonasPanel state={personas} />
      </section>

      <section className="section" aria-labelledby="simulation-title">
        <div className="section__header">
          <h2 className="section__title" id="simulation-title">
            Access Policy Simulation
          </h2>
          <p className="section__note">POST /api/v1/readiness/access-policy</p>
        </div>
        <div className="search-form readiness-form">
          <label className="search-form__label" htmlFor="persona-select">
            persona_id
          </label>
          <div className="search-form__row">
            <select
              className="search-form__input"
              id="persona-select"
              value={selectedPersonaId}
              disabled={!personas.data?.items.length}
              onChange={(event) => setSelectedPersonaId(event.target.value)}
            >
              {(personas.data?.items ?? []).map((persona) => (
                <option key={persona.persona_id} value={persona.persona_id}>
                  {persona.persona_id}
                </option>
              ))}
            </select>
            <button
              className="primary-button"
              type="button"
              disabled={!selectedPersonaId || policy.loading}
              onClick={runSimulation}
            >
              {policy.loading ? "Running" : "Run Simulation"}
            </button>
          </div>
          <p className="status-text">
            Sample request: Finance or Human Resources, APAC or EU, policy or manual,
            internal or confidential, Finance Operations or Data Protection Office.
          </p>
        </div>
        {selectedPersona ? <PersonaSummary persona={selectedPersona} /> : null}
        <PolicyResult state={policy} />
      </section>

      <section className="section" aria-labelledby="metadata-title">
        <div className="section__header">
          <h2 className="section__title" id="metadata-title">
            Metadata Distributions
          </h2>
          <p className="section__note">derived from processed document metadata</p>
        </div>
        {summary.data ? (
          <DistributionGrid distributions={summary.data.corpus_metadata_distributions} />
        ) : (
          <EmptyPanel title="Metadata unavailable" description="Readiness summary is unavailable." />
        )}
      </section>

      <section className="section" aria-labelledby="artifact-status-title">
        <div className="section__header">
          <h2 className="section__title" id="artifact-status-title">
            Local Artifact Status
          </h2>
          <p className="section__note">derived without rebuilds</p>
        </div>
        <div className="evaluation-details">
          <StatusPanel title="graph_status" payload={summary.data?.graph_status} />
          <StatusPanel title="evaluation_status" payload={summary.data?.evaluation_status} />
          <StatusPanel title="governance_status" payload={summary.data?.governance_status} />
          <StatusPanel title="access_levels" payload={summary.data?.access_levels} />
        </div>
      </section>
    </>
  );
}

function ReadinessMetric({
  label,
  value,
  state,
  detail
}: {
  label: string;
  value: number | null | undefined;
  state: LoadState<unknown>;
  detail?: string;
}) {
  let displayValue = value ?? "Unavailable";
  let displayDetail = detail ?? "local summary";

  if (state.loading) {
    displayValue = "...";
    displayDetail = "Loading";
  } else if (state.error) {
    displayValue = "--";
    displayDetail = state.error;
  }

  return (
    <article className="metric-card">
      <span className="metric-card__value metric-card__value--compact">{displayValue}</span>
      <h3>{label}</h3>
      <p className={state.error ? "status-text status-text--error" : "status-text"}>{displayDetail}</p>
    </article>
  );
}

function PersonasPanel({ state }: { state: LoadState<PersonaListResponse> }) {
  if (state.loading) {
    return <EmptyPanel title="Loading personas" description="Reading simulated enterprise personas." />;
  }
  if (state.error) {
    return <EmptyPanel title="Personas unavailable" description={state.error} tone="error" />;
  }
  if (!state.data || state.data.items.length === 0) {
    return <EmptyPanel title="No personas available" description="No simulated personas were returned." />;
  }
  return (
    <div className="persona-grid">
      {state.data.items.map((persona) => (
        <article className="feature-card" key={persona.persona_id}>
          <h3>{persona.display_name}</h3>
          <dl className="source-info">
            <div>
              <dt>persona_id</dt>
              <dd>{persona.persona_id}</dd>
            </div>
            <div>
              <dt>department</dt>
              <dd>{persona.department}</dd>
            </div>
            <div>
              <dt>regions</dt>
              <dd>{persona.regions.join(", ")}</dd>
            </div>
            <div>
              <dt>max_access_level</dt>
              <dd>{persona.max_access_level}</dd>
            </div>
          </dl>
          <p>{persona.description}</p>
        </article>
      ))}
    </div>
  );
}

function PersonaSummary({ persona }: { persona: PersonaListResponse["items"][number] }) {
  return (
    <div className="panel readiness-persona-summary">
      <h3>{persona.display_name}</h3>
      <pre className="json-panel">
        {JSON.stringify(
          {
            persona_id: persona.persona_id,
            department: persona.department,
            regions: persona.regions,
            max_access_level: persona.max_access_level,
            allowed_policy_types: persona.allowed_policy_types
          },
          null,
          2
        )}
      </pre>
    </div>
  );
}

function PolicyResult({ state }: { state: LoadState<AccessPolicyResponse> }) {
  if (state.loading) {
    return <EmptyPanel title="Running simulation" description="Generating simulation-only metadata filters." />;
  }
  if (state.error) {
    return <EmptyPanel title="Simulation unavailable" description={state.error} tone="error" />;
  }
  if (!state.data) {
    return (
      <EmptyPanel
        title="No simulation result yet"
        description="Choose a persona and run the sample request to inspect allowed_filters and denied_reasons."
      />
    );
  }
  return (
    <div className="evidence-viewer readiness-result">
      <div className="evidence-column">
        <h3>allowed_filters</h3>
        <pre className="json-panel">{JSON.stringify(state.data.allowed_filters, null, 2)}</pre>
      </div>
      <div className="evidence-column">
        <h3>denied_reasons</h3>
        {state.data.denied_reasons.length > 0 ? (
          <ul className="boundary-list">
            {state.data.denied_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <p className="status-text">No requested filters were denied.</p>
        )}
      </div>
      <div className="evidence-column evidence-column--wide">
        <h3>explanation</h3>
        <p>{state.data.explanation}</p>
      </div>
    </div>
  );
}

function DistributionGrid({ distributions }: { distributions: CorpusMetadataDistributions }) {
  return (
    <div className="breakdown-grid">
      <BreakdownCard title="departments" values={distributions.departments} />
      <BreakdownCard title="regions" values={distributions.regions} />
      <BreakdownCard title="policy_types" values={distributions.policy_types} />
      <BreakdownCard title="owners" values={distributions.owners} />
      <BreakdownCard title="access_levels" values={distributions.access_levels} />
    </div>
  );
}

function BreakdownCard({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values);
  return (
    <article className="breakdown-card">
      <div className="breakdown-card__header">
        <h3>{title}</h3>
        <span>{entries.length} values</span>
      </div>
      {entries.length > 0 ? (
        <dl className="breakdown-list">
          {entries.map(([key, value]) => (
            <div className="breakdown-list__row" key={key}>
              <dt>{key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="status-text">Unavailable</p>
      )}
    </article>
  );
}

function StatusPanel({ title, payload }: { title: string; payload: unknown }) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      {payload ? (
        <pre className="json-panel">{JSON.stringify(payload, null, 2)}</pre>
      ) : (
        <p className="status-text">Unavailable</p>
      )}
    </div>
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
  return "API unavailable";
}
