import { useCallback, useEffect, useMemo, useState } from "react";

import {
  getReadinessPersonas,
  simulateAccessPolicy,
  type AccessPolicyResponse,
  type PersonaListResponse,
  type SearchFilters,
  type SimulatedPersona
} from "../api";

export type SimulationApplicationStatus = "disabled" | "ready" | "applied" | "blocked" | "unavailable";

export type AccessPolicySimulationController = {
  enabled: boolean;
  setEnabled: (enabled: boolean) => void;
  personas: SimulatedPersona[];
  personasLoading: boolean;
  personasError: string | null;
  selectedPersonaId: string;
  setSelectedPersonaId: (personaId: string) => void;
  selectedPersona: SimulatedPersona | null;
  policy: AccessPolicyResponse | null;
  policyLoading: boolean;
  policyError: string | null;
  runSimulation: () => Promise<AccessPolicyResponse | null>;
};

export function useAccessPolicySimulation(defaultPersonaId = "finance_manager_apac"): AccessPolicySimulationController {
  const [enabled, setEnabled] = useState(false);
  const [personas, setPersonas] = useState<PersonaListResponse | null>(null);
  const [personasLoading, setPersonasLoading] = useState(false);
  const [personasError, setPersonasError] = useState<string | null>(null);
  const [selectedPersonaId, setSelectedPersonaId] = useState(defaultPersonaId);
  const [policy, setPolicy] = useState<AccessPolicyResponse | null>(null);
  const [policyLoading, setPolicyLoading] = useState(false);
  const [policyError, setPolicyError] = useState<string | null>(null);

  useEffect(() => {
    if (!enabled || personas || personasLoading) {
      return;
    }

    let active = true;
    setPersonasLoading(true);

    getReadinessPersonas()
      .then((data) => {
        if (!active) {
          return;
        }
        setPersonas(data);
        setPersonasLoading(false);
        setPersonasError(null);
        if (!data.items.some((persona) => persona.persona_id === selectedPersonaId) && data.items[0]) {
          setSelectedPersonaId(data.items[0].persona_id);
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setPersonas(null);
          setPersonasLoading(false);
          setPersonasError(messageFor(error));
        }
      });

    return () => {
      active = false;
    };
  }, [enabled, personas, personasLoading, selectedPersonaId]);

  const selectedPersona = useMemo(
    () => personas?.items.find((persona) => persona.persona_id === selectedPersonaId) ?? null,
    [personas, selectedPersonaId]
  );

  const runSimulation = useCallback(async () => {
    if (!enabled || !selectedPersonaId || !personas?.items.length) {
      return null;
    }
    setPolicyLoading(true);
    setPolicyError(null);
    try {
      const response = await simulateAccessPolicy({ persona_id: selectedPersonaId });
      setPolicy(response);
      return response;
    } catch (error: unknown) {
      setPolicy(null);
      setPolicyError(messageFor(error));
      return null;
    } finally {
      setPolicyLoading(false);
    }
  }, [enabled, personas, selectedPersonaId]);

  return {
    enabled,
    setEnabled,
    personas: personas?.items ?? [],
    personasLoading,
    personasError,
    selectedPersonaId,
    setSelectedPersonaId,
    selectedPersona,
    policy,
    policyLoading,
    policyError,
    runSimulation
  };
}

export function filtersFromAccessPolicy(policy: AccessPolicyResponse): SearchFilters {
  return {
    ...(policy.allowed_filters.departments.length ? { departments: policy.allowed_filters.departments } : {}),
    ...(policy.allowed_filters.regions.length ? { regions: policy.allowed_filters.regions } : {}),
    ...(policy.allowed_filters.policy_types.length ? { policy_types: policy.allowed_filters.policy_types } : {}),
    ...(policy.allowed_filters.owners.length ? { owners: policy.allowed_filters.owners } : {}),
    ...(policy.allowed_filters.access_levels.length ? { access_levels: policy.allowed_filters.access_levels } : {})
  };
}

export function isAccessPolicyBlocked(policy: AccessPolicyResponse): boolean {
  return Object.values(policy.allowed_filters).every((values) => values.length === 0) && policy.denied_reasons.length > 0;
}

export function AccessPolicySimulationPanel({
  controller,
  applicationStatus,
  appliedDescription
}: {
  controller: AccessPolicySimulationController;
  applicationStatus: SimulationApplicationStatus;
  appliedDescription: string;
}) {
  const effectiveStatus =
    controller.enabled && applicationStatus === "disabled" ? "ready" : applicationStatus;
  const effectiveDescription =
    controller.enabled && applicationStatus === "disabled"
      ? "Enabled. Preview policy or submit the request to generate simulation-only filters."
      : appliedDescription;

  return (
    <div className="simulation-panel">
      <label className="checkbox-row simulation-panel__toggle">
        <input
          type="checkbox"
          checked={controller.enabled}
          onChange={(event) => controller.setEnabled(event.target.checked)}
        />
        <span>Enable simulation-only persona filters</span>
      </label>

      {!controller.enabled ? (
        <p className="status-text">
          Disabled. Requests are sent with the same payload shape as the default Studio experience.
        </p>
      ) : (
        <>
          <div className="simulation-panel__controls">
            <label className="search-form__label" htmlFor="access-persona-select">
              persona_id
            </label>
            <div className="search-form__row">
              <select
                className="search-form__input"
                id="access-persona-select"
                value={controller.selectedPersonaId}
                disabled={controller.personasLoading || controller.personas.length === 0}
                onChange={(event) => controller.setSelectedPersonaId(event.target.value)}
              >
                {controller.personas.map((persona) => (
                  <option key={persona.persona_id} value={persona.persona_id}>
                    {persona.persona_id}
                  </option>
                ))}
              </select>
              <button
                className="primary-button"
                type="button"
                disabled={controller.policyLoading || controller.personas.length === 0}
                onClick={() => void controller.runSimulation()}
              >
                {controller.policyLoading ? "Simulating" : "Preview Policy"}
              </button>
            </div>
          </div>

          {controller.personasLoading ? (
            <p className="status-text">Loading simulated personas.</p>
          ) : null}
          {controller.personasError ? (
            <div className="inline-alert">GET /api/v1/readiness/personas: {controller.personasError}</div>
          ) : null}
          {controller.policyError ? (
            <div className="inline-alert">POST /api/v1/readiness/access-policy: {controller.policyError}</div>
          ) : null}

          <SimulationStatus status={effectiveStatus} description={effectiveDescription} />

          {controller.selectedPersona ? <SelectedPersonaCard persona={controller.selectedPersona} /> : null}
          {controller.policy ? <PolicyDetails policy={controller.policy} /> : null}
        </>
      )}
    </div>
  );
}

function SimulationStatus({
  status,
  description
}: {
  status: SimulationApplicationStatus;
  description: string;
}) {
  return (
    <div className="simulation-panel__status">
      <span className={`status-pill status-pill--${status === "blocked" || status === "unavailable" ? "open" : "ready"}`}>
        {status}
      </span>
      <p>{description}</p>
    </div>
  );
}

function SelectedPersonaCard({ persona }: { persona: SimulatedPersona }) {
  return (
    <div className="panel simulation-panel__persona">
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
    </div>
  );
}

function PolicyDetails({ policy }: { policy: AccessPolicyResponse }) {
  return (
    <div className="evidence-viewer simulation-panel__details">
      <div className="evidence-column">
        <h3>allowed_filters</h3>
        <pre className="json-panel">{JSON.stringify(policy.allowed_filters, null, 2)}</pre>
      </div>
      <div className="evidence-column">
        <h3>denied_reasons</h3>
        {policy.denied_reasons.length > 0 ? (
          <ul className="boundary-list">
            {policy.denied_reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        ) : (
          <p className="status-text">No requested filters were denied.</p>
        )}
      </div>
      <div className="evidence-column evidence-column--wide">
        <h3>explanation</h3>
        <p>{policy.explanation}</p>
      </div>
    </div>
  );
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Backend unavailable";
}
