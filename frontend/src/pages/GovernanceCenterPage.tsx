import { useEffect, useMemo, useState } from "react";

import { getFeedbackList, type FeedbackListResponse, type FeedbackRecord } from "../api";

type GovernanceState = {
  data: FeedbackListResponse | null;
  loading: boolean;
  error: string | null;
};

export function GovernanceCenterPage() {
  const [state, setState] = useState<GovernanceState>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let active = true;

    getFeedbackList()
      .then((data) => {
        if (active) {
          setState({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({ data: null, loading: false, error: messageFor(error) });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  return (
    <>
      <section className="page-heading" aria-labelledby="governance-title">
        <p className="hero__eyebrow">Feedback governance visibility</p>
        <h1 className="page-heading__title" id="governance-title">
          Governance Center
        </h1>
        <p className="page-heading__subtitle">
          Read-only view of existing local feedback records, review status distribution,
          issue categories, and evaluation case linkage.
        </p>
      </section>

      {state.loading ? (
        <section className="section">
          <EmptyPanel title="Loading feedback records" description="Reading local feedback governance data." />
        </section>
      ) : (
        <GovernanceContent state={state} />
      )}
    </>
  );
}

function GovernanceContent({ state }: { state: GovernanceState }) {
  const items = state.data?.items ?? [];
  const summary = state.data?.summary;
  const userRatingBreakdown = useMemo(() => countBy(items, "user_rating"), [items]);
  const linkedEvalCount = useMemo(
    () => items.filter((item) => Boolean(item.linked_eval_case_id)).length,
    [items]
  );

  if (state.error) {
    return (
      <section className="section">
        <EmptyPanel title="Governance data unavailable" description={state.error} tone="error" />
      </section>
    );
  }

  return (
    <>
      <section className="section" aria-labelledby="governance-overview-title">
        <div className="section__header">
          <h2 className="section__title" id="governance-overview-title">
            Governance Overview
          </h2>
          <p className="section__note">GET /api/v1/feedback</p>
        </div>
        <div className="metric-grid">
          <MetricCard
            label="total feedback records"
            value={formatNumber(summary?.total_count ?? state.data?.total)}
            detail="from FeedbackListResponse"
          />
          <MetricCard
            label="unresolved_count"
            value={formatNumber(summary?.unresolved_count)}
            detail={detailFor(summary?.unresolved_count)}
          />
          <MetricCard
            label="negative_count"
            value={formatNumber(summary?.negative_count)}
            detail={detailFor(summary?.negative_count)}
          />
          <MetricCard
            label="linked_eval_case_id"
            value={formatNumber(linkedEvalCount)}
            detail="derived from returned records"
          />
        </div>
      </section>

      <section className="section" aria-labelledby="governance-breakdowns-title">
        <div className="section__header">
          <h2 className="section__title" id="governance-breakdowns-title">
            Governance Breakdowns
          </h2>
          <p className="section__note">Backend summary fields, plus local user_rating count</p>
        </div>
        <div className="breakdown-grid">
          <BreakdownPanel title="by_review_status" values={summary?.by_review_status} />
          <BreakdownPanel title="by_feedback_type" values={summary?.by_feedback_type} />
          <BreakdownPanel title="by_issue_category" values={summary?.by_issue_category} />
          <BreakdownPanel title="user_rating" values={userRatingBreakdown} note="derived from items" />
        </div>
      </section>

      <section className="section" aria-labelledby="linked-evaluation-title">
        <div className="section__header">
          <h2 className="section__title" id="linked-evaluation-title">
            Linked Evaluation Case Visibility
          </h2>
          <p className="section__note">{linkedEvalCount} records with linked_eval_case_id</p>
        </div>
        {linkedEvalCount > 0 ? (
          <pre className="json-panel">
            {JSON.stringify(
              items
                .filter((item) => item.linked_eval_case_id)
                .map((item) => ({
                  feedback_id: item.feedback_id,
                  linked_eval_case_id: item.linked_eval_case_id
                })),
              null,
              2
            )}
          </pre>
        ) : (
          <EmptyPanel
            title="No linked evaluation cases"
            description="No returned feedback records currently include linked_eval_case_id."
          />
        )}
      </section>

      <section className="section" aria-labelledby="feedback-list-title">
        <div className="section__header">
          <h2 className="section__title" id="feedback-list-title">
            Feedback Records
          </h2>
          <p className="section__note">
            {state.data ? `${state.data.total} total records, showing ${items.length}` : "Feedback list"}
          </p>
        </div>
        <FeedbackTable items={items} />
      </section>
    </>
  );
}

function FeedbackTable({ items }: { items: FeedbackRecord[] }) {
  if (items.length === 0) {
    return (
      <EmptyPanel
        title="No feedback records"
        description="No local feedback governance records are currently visible."
      />
    );
  }

  return (
    <div className="table-shell">
      <table className="asset-table governance-table">
        <thead>
          <tr>
            <th>feedback_id</th>
            <th>timestamp</th>
            <th>feedback_type</th>
            <th>issue_category</th>
            <th>user_rating</th>
            <th>review_status</th>
            <th>linked_eval_case_id</th>
            <th>query or answer preview</th>
            <th>reviewer_note</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.feedback_id}>
              <td className="asset-table__id">{item.feedback_id}</td>
              <td>{formatTimestamp(item.timestamp)}</td>
              <td>{item.feedback_type}</td>
              <td>{item.issue_category}</td>
              <td>{item.user_rating}</td>
              <td>
                <span className={`status-pill ${statusClassFor(item.review_status)}`}>{item.review_status}</span>
              </td>
              <td>{item.linked_eval_case_id ?? "Unavailable"}</td>
              <td className="governance-table__preview">{previewFor(item)}</td>
              <td>{item.reviewer_note ?? "Unavailable"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BreakdownPanel({
  title,
  values,
  note
}: {
  title: string;
  values: Record<string, number> | undefined;
  note?: string;
}) {
  const entries = Object.entries(values ?? {}).sort(([left], [right]) => left.localeCompare(right));

  return (
    <article className="breakdown-card">
      <div className="breakdown-card__header">
        <h3>{title}</h3>
        {note ? <span>{note}</span> : null}
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

function MetricCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <article className="metric-card">
      <span className="metric-card__value metric-card__value--compact">{value}</span>
      <h3>{label}</h3>
      <p className={detail === "Unavailable" ? "status-text status-text--error" : "status-text"}>{detail}</p>
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

function countBy<T extends Record<K, string | null | undefined>, K extends keyof T>(
  items: T[],
  key: K
): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = item[key] ?? "Unavailable";
    counts[value] = (counts[value] ?? 0) + 1;
    return counts;
  }, {});
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return String(value);
}

function detailFor(value: number | null | undefined): string {
  return value === null || value === undefined ? "Unavailable" : "local feedback summary";
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) {
    return "Unavailable";
  }

  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function previewFor(item: FeedbackRecord): string {
  const source = item.query || item.answer || "";
  if (!source) {
    return "Unavailable";
  }
  return source.length > 160 ? `${source.slice(0, 157)}...` : source;
}

function statusClassFor(status: string): string {
  if (status === "resolved") {
    return "status-pill--ready";
  }
  if (status === "open") {
    return "status-pill--open";
  }
  return "status-pill--neutral";
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "API unavailable";
}
