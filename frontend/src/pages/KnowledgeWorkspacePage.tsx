import { useEffect, useState } from "react";

import {
  getDocuments,
  getWorkspaceSummary,
  type DocumentSummary,
  type PaginatedDocumentsResponse,
  type WorkspaceSummary
} from "../api";

type LoadState<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

const pipelineSteps = [
  "Documents",
  "Chunking",
  "Retrieval",
  "Graph",
  "Evaluation",
  "Governance"
] as const;

export function KnowledgeWorkspacePage() {
  const [summary, setSummary] = useState<LoadState<WorkspaceSummary>>({
    data: null,
    loading: true,
    error: null
  });
  const [documents, setDocuments] = useState<LoadState<PaginatedDocumentsResponse>>({
    data: null,
    loading: true,
    error: null
  });

  useEffect(() => {
    let active = true;

    getWorkspaceSummary()
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

    getDocuments()
      .then((data) => {
        if (active) {
          setDocuments({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setDocuments({ data: null, loading: false, error: messageFor(error) });
        }
      });

    return () => {
      active = false;
    };
  }, []);

  const documentItems = documents.data?.items ?? [];
  const hasDocuments = documentItems.length > 0;
  const pipelineStatus = buildPipelineStatus(summary.data, hasDocuments);

  return (
    <>
      <section className="page-heading" aria-labelledby="workspace-title">
        <p className="hero__eyebrow">Knowledge assets</p>
        <h1 className="page-heading__title" id="workspace-title">
          Knowledge Workspace
        </h1>
        <p className="page-heading__subtitle">
          Product-facing visibility into processed enterprise documents and the local
          KnowledgeOps pipeline state.
        </p>
      </section>

      <section className="section" aria-labelledby="workspace-overview-title">
        <div className="section__header">
          <h2 className="section__title" id="workspace-overview-title">
            Workspace Overview
          </h2>
          <p className="section__note">Read-only summary from local artifacts</p>
        </div>
        <div className="metric-grid">
          <WorkspaceMetric label="Documents" state={summary} value={summary.data?.documents} />
          <WorkspaceMetric label="Chunks" state={summary} value={summary.data?.chunks} />
          <WorkspaceMetric label="Graph Nodes" state={summary} value={summary.data?.graph_nodes} />
          <WorkspaceMetric label="Graph Edges" state={summary} value={summary.data?.graph_edges} />
        </div>
      </section>

      <section className="section" aria-labelledby="asset-inventory-title">
        <div className="section__header">
          <h2 className="section__title" id="asset-inventory-title">
            Knowledge Asset Inventory
          </h2>
          <p className="section__note">
            {documents.data ? `${documents.data.total} available documents` : "Document metadata"}
          </p>
        </div>
        <DocumentInventory state={documents} />
      </section>

      <section className="section" aria-labelledby="pipeline-status-title">
        <div className="section__header">
          <h2 className="section__title" id="pipeline-status-title">
            Processing Pipeline Status
          </h2>
          <p className="section__note">Visibility only, no operational actions</p>
        </div>
        <div className="pipeline-status">
          {pipelineStatus.map((step) => (
            <article className={`pipeline-step pipeline-step--${step.state}`} key={step.label}>
              <span className="pipeline-step__indicator" aria-hidden="true" />
              <h3>{step.label}</h3>
              <p>{step.description}</p>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function WorkspaceMetric({
  label,
  state,
  value
}: {
  label: string;
  state: LoadState<unknown>;
  value: number | null | undefined;
}) {
  let displayValue = value ?? "Unavailable";
  let detail = "Local summary";

  if (state.loading) {
    displayValue = "...";
    detail = "Loading";
  } else if (state.error) {
    displayValue = "--";
    detail = state.error;
  }

  return (
    <article className="metric-card">
      <span className="metric-card__value">{displayValue}</span>
      <h3>{label}</h3>
      <p className={state.error ? "status-text status-text--error" : "status-text"}>{detail}</p>
    </article>
  );
}

function DocumentInventory({ state }: { state: LoadState<PaginatedDocumentsResponse> }) {
  if (state.loading) {
    return <EmptyPanel title="Loading inventory" description="Reading document metadata." />;
  }

  if (state.error) {
    return <EmptyPanel title="Inventory unavailable" description={state.error} tone="error" />;
  }

  if (!state.data || state.data.items.length === 0) {
    return (
      <EmptyPanel
        title="No documents available"
        description="No processed enterprise knowledge assets are currently visible."
      />
    );
  }

  return (
    <div className="table-shell">
      <table className="asset-table">
        <thead>
          <tr>
            <th>Document ID</th>
            <th>Title</th>
            <th>Source Filename</th>
            <th>Status</th>
            <th>Chunks</th>
          </tr>
        </thead>
        <tbody>
          {state.data.items.map((document) => (
            <DocumentRow document={document} key={document.metadata.doc_id} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DocumentRow({ document }: { document: DocumentSummary }) {
  return (
    <tr>
      <td className="asset-table__id">{document.metadata.doc_id}</td>
      <td>{document.metadata.title}</td>
      <td>{sourceFilename(document.metadata.source_file)}</td>
      <td>
        <span className="status-pill status-pill--ready">Processed</span>
      </td>
      <td>{document.chunk_count}</td>
    </tr>
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

function buildPipelineStatus(summary: WorkspaceSummary | null, hasDocuments: boolean) {
  const documentsReady = Boolean(summary && summary.documents > 0 && hasDocuments);
  const chunkingReady = Boolean(summary && summary.chunks > 0);
  const graphReady = Boolean(summary && summary.graph_nodes > 0 && summary.graph_edges > 0);

  return pipelineSteps.map((label) => {
    if (label === "Documents") {
      return {
        label,
        state: documentsReady ? "ready" : "missing",
        description: documentsReady ? "Processed assets visible" : "No processed assets visible"
      };
    }
    if (label === "Chunking") {
      return {
        label,
        state: chunkingReady ? "ready" : "missing",
        description: chunkingReady ? "Chunks available for retrieval" : "Chunk artifacts missing"
      };
    }
    if (label === "Graph") {
      return {
        label,
        state: graphReady ? "ready" : "missing",
        description: graphReady ? "Graph artifact available" : "Graph artifact missing"
      };
    }
    if (label === "Retrieval") {
      return {
        label,
        state: chunkingReady ? "ready" : "unknown",
        description: chunkingReady ? "Uses processed chunks" : "Waiting on chunk artifacts"
      };
    }
    if (label === "Evaluation") {
      return {
        label,
        state: chunkingReady && graphReady ? "ready" : "unknown",
        description: chunkingReady && graphReady ? "Evaluation preconditions visible" : "Depends on local reports"
      };
    }
    return {
      label,
      state: documentsReady ? "ready" : "unknown",
      description: documentsReady ? "Feedback loop can reference assets" : "Waiting on assets"
    };
  });
}

function sourceFilename(sourceFile: string): string {
  return sourceFile.split("/").pop() || sourceFile;
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "API unavailable";
}
