import { useEffect, useState } from "react";

import {
  getEvaluationCases,
  getEvaluationLatest,
  getEvaluationSummary,
  type EvaluationCasesResponse,
  type EvaluationReport,
  type EvaluationSummary
} from "../api";

type EvaluationCenterState = {
  summary: EvaluationSummary | null;
  report: EvaluationReport | null;
  cases: EvaluationCasesResponse | null;
  loading: boolean;
  summaryError: string | null;
  latestError: string | null;
  casesError: string | null;
};

export function EvaluationCenterPage() {
  const [state, setState] = useState<EvaluationCenterState>({
    summary: null,
    report: null,
    cases: null,
    loading: true,
    summaryError: null,
    latestError: null,
    casesError: null
  });

  useEffect(() => {
    let active = true;

    Promise.allSettled([getEvaluationSummary(), getEvaluationLatest(), getEvaluationCases()]).then(
      ([summaryResult, latestResult, casesResult]) => {
        if (!active) {
          return;
        }

        setState({
          summary: summaryResult.status === "fulfilled" ? summaryResult.value : null,
          report: latestResult.status === "fulfilled" ? latestResult.value.report : null,
          cases: casesResult.status === "fulfilled" ? casesResult.value : null,
          loading: false,
          summaryError: summaryResult.status === "rejected" ? messageFor(summaryResult.reason) : null,
          latestError: latestResult.status === "rejected" ? messageFor(latestResult.reason) : null,
          casesError: casesResult.status === "rejected" ? messageFor(casesResult.reason) : null
        });
      }
    );

    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <section className="page-heading" aria-labelledby="evaluation-title">
        <p className="hero__eyebrow">Deterministic quality inspection</p>
        <h1 className="page-heading__title" id="evaluation-title">
          Evaluation Center
        </h1>
        <p className="page-heading__subtitle">
          Read-only view of the latest local evaluation artifacts, case inventory, and
          deterministic KnowledgeOps quality metrics.
        </p>
      </section>

      {state.loading ? (
        <section className="section">
          <EmptyPanel title="Loading evaluation metrics" description="Reading local evaluation artifacts." />
        </section>
      ) : (
        <EvaluationContent state={state} />
      )}
    </>
  );
}

function EvaluationContent({ state }: { state: EvaluationCenterState }) {
  const totalCases = state.report?.total_cases ?? state.summary?.total_cases ?? state.cases?.total_cases ?? null;
  const passedCases = state.report?.passed_cases ?? state.summary?.passed_cases ?? null;
  const failedCases = state.report?.failed_cases ?? state.summary?.failed_cases ?? null;
  const passRate = state.report?.metrics.pass_rate ?? state.summary?.pass_rate ?? null;

  return (
    <>
      {state.summaryError || state.latestError || state.casesError ? (
        <section className="section">
          <div className="inline-alert">
            {state.summaryError ? <p>GET /api/v1/evaluation/summary: {state.summaryError}</p> : null}
            {state.latestError ? <p>GET /api/v1/evaluation/latest: {state.latestError}</p> : null}
            {state.casesError ? <p>GET /api/v1/evaluation/cases: {state.casesError}</p> : null}
          </div>
        </section>
      ) : null}

      <section className="section" aria-labelledby="evaluation-overview-title">
        <div className="section__header">
          <h2 className="section__title" id="evaluation-overview-title">
            Evaluation Overview
          </h2>
          <p className="section__note">{state.report ? state.report.run_id : "latest report unavailable"}</p>
        </div>
        <div className="metric-grid">
          <MetricCard label="total_cases" value={formatNumber(totalCases)} detail={detailFor(totalCases)} />
          <MetricCard label="passed_cases" value={formatNumber(passedCases)} detail={detailFor(passedCases)} />
          <MetricCard label="failed_cases" value={formatNumber(failedCases)} detail={detailFor(failedCases)} />
          <MetricCard label="pass_rate" value={formatMetric(passRate)} detail={detailFor(passRate)} />
        </div>
      </section>

      <section className="section" aria-labelledby="retrieval-metrics-title">
        <div className="section__header">
          <h2 className="section__title" id="retrieval-metrics-title">
            Retrieval Metrics
          </h2>
          <p className="section__note">from EvaluationReport.metrics</p>
        </div>
        <div className="metric-grid">
          <MetricCard
            label="retrieval_hit_at_k"
            value={formatMetric(state.report?.metrics.retrieval_hit_at_k)}
            detail={detailFor(state.report?.metrics.retrieval_hit_at_k)}
          />
          <MetricCard
            label="retrieval_recall_at_k"
            value={formatMetric(state.report?.metrics.retrieval_recall_at_k)}
            detail={detailFor(state.report?.metrics.retrieval_recall_at_k)}
          />
          <MetricCard
            label="expected_chunk_presence_rate"
            value={formatMetric(state.report?.metrics.expected_chunk_presence_rate)}
            detail={detailFor(state.report?.metrics.expected_chunk_presence_rate)}
          />
          <MetricCard
            label="route_accuracy"
            value={formatMetric(state.report?.metrics.route_accuracy ?? state.summary?.route_accuracy)}
            detail={detailFor(state.report?.metrics.route_accuracy ?? state.summary?.route_accuracy)}
          />
        </div>
      </section>

      <section className="section" aria-labelledby="citation-metrics-title">
        <div className="section__header">
          <h2 className="section__title" id="citation-metrics-title">
            Citation Metrics
          </h2>
          <p className="section__note">backend citation and grounding checks</p>
        </div>
        <div className="metric-grid">
          <MetricCard
            label="answer_citation_non_empty_rate"
            value={formatMetric(state.report?.metrics.answer_citation_non_empty_rate)}
            detail={detailFor(state.report?.metrics.answer_citation_non_empty_rate)}
          />
          <MetricCard
            label="citation_validity_rate"
            value={formatMetric(state.report?.metrics.citation_validity_rate ?? state.summary?.citation_validity_rate)}
            detail={detailFor(state.report?.metrics.citation_validity_rate ?? state.summary?.citation_validity_rate)}
          />
          <MetricCard
            label="expected_citation_match_rate"
            value={formatMetric(state.report?.metrics.expected_citation_match_rate)}
            detail={detailFor(state.report?.metrics.expected_citation_match_rate)}
          />
          <MetricCard
            label="grounded_answer_pass_rate"
            value={formatMetric(state.report?.metrics.grounded_answer_pass_rate ?? state.summary?.grounded_answer_pass_rate)}
            detail={detailFor(state.report?.metrics.grounded_answer_pass_rate ?? state.summary?.grounded_answer_pass_rate)}
          />
        </div>
      </section>

      <section className="section" aria-labelledby="refusal-metrics-title">
        <div className="section__header">
          <h2 className="section__title" id="refusal-metrics-title">
            Refusal And Fabrication Metrics
          </h2>
          <p className="section__note">deterministic refusal and fabricated-answer checks</p>
        </div>
        <div className="metric-grid">
          <MetricCard
            label="fabricated_answer_rate"
            value={formatMetric(state.report?.metrics.fabricated_answer_rate ?? state.summary?.fabricated_answer_rate)}
            detail={detailFor(state.report?.metrics.fabricated_answer_rate ?? state.summary?.fabricated_answer_rate)}
          />
          <MetricCard
            label="refusal_accuracy"
            value={formatMetric(state.report?.metrics.refusal_accuracy ?? state.summary?.refusal_accuracy)}
            detail={detailFor(state.report?.metrics.refusal_accuracy ?? state.summary?.refusal_accuracy)}
          />
          <MetricCard
            label="out_of_scope_refusal_accuracy"
            value={formatMetric(state.report?.metrics.out_of_scope_refusal_accuracy)}
            detail={detailFor(state.report?.metrics.out_of_scope_refusal_accuracy)}
          />
          <MetricCard
            label="unsupported_refusal_accuracy"
            value={formatMetric(state.report?.metrics.unsupported_refusal_accuracy)}
            detail={detailFor(state.report?.metrics.unsupported_refusal_accuracy)}
          />
        </div>
      </section>

      <section className="section" aria-labelledby="dataset-title">
        <div className="section__header">
          <h2 className="section__title" id="dataset-title">
            Dataset And Latest Report
          </h2>
          <p className="section__note">{state.cases?.dataset_version ?? state.report?.dataset_version ?? "dataset unavailable"}</p>
        </div>
        <div className="evaluation-details">
          <div className="panel">
            <h3>split_metrics</h3>
            {state.report ? (
              <pre className="json-panel">{JSON.stringify(state.report.split_metrics, null, 2)}</pre>
            ) : (
              <p className="status-text">Unavailable until GET /api/v1/evaluation/latest returns a report.</p>
            )}
          </div>
          <div className="panel">
            <h3>cases</h3>
            {state.cases ? (
              <pre className="json-panel">
                {JSON.stringify(
                  {
                    request_id: state.cases.request_id,
                    dataset_version: state.cases.dataset_version,
                    total_cases: state.cases.total_cases
                  },
                  null,
                  2
                )}
              </pre>
            ) : (
              <p className="status-text">Evaluation case inventory unavailable.</p>
            )}
          </div>
        </div>
      </section>

      {!state.summary?.available && !state.report ? (
        <section className="section">
          <EmptyPanel
            title="No latest evaluation report"
            description="GET /api/v1/evaluation/summary reported available=false. Run state is shown as unavailable without changing backend behavior."
          />
        </section>
      ) : null}
    </>
  );
}

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span className="metric-card__value metric-card__value--compact">{value}</span>
      <h3>{label}</h3>
      <p className={detail === "Unavailable" ? "status-text status-text--error" : "status-text"}>{detail}</p>
    </article>
  );
}

function EmptyPanel({ title, description }: { title: string; description: string }) {
  return (
    <div className="empty-panel">
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return `${Math.round(value * 1000) / 10}%`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return String(value);
}

function detailFor(value: number | null | undefined): string {
  return value === null || value === undefined ? "Unavailable" : "local artifact";
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "API unavailable";
}
