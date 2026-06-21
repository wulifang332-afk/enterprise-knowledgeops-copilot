import { useEffect, useMemo, useState } from "react";

import {
  getGraphEdges,
  getGraphNeighborhood,
  getGraphNodes,
  type GraphEdgeListResponse,
  type GraphNeighborhoodResponse,
  type GraphNodeListResponse,
  type KnowledgeGraphEdge,
  type KnowledgeGraphNode
} from "../api";

type GraphExplorerState = {
  nodes: GraphNodeListResponse | null;
  edges: GraphEdgeListResponse | null;
  loading: boolean;
  nodesError: string | null;
  edgesError: string | null;
};

type NeighborhoodState = {
  data: GraphNeighborhoodResponse | null;
  loading: boolean;
  error: string | null;
};

export function GraphExplorerPage() {
  const [state, setState] = useState<GraphExplorerState>({
    nodes: null,
    edges: null,
    loading: true,
    nodesError: null,
    edgesError: null
  });
  const [selectedNodeId, setSelectedNodeId] = useState("");
  const [neighborhood, setNeighborhood] = useState<NeighborhoodState>({
    data: null,
    loading: false,
    error: null
  });

  useEffect(() => {
    let active = true;

    Promise.allSettled([getGraphNodes(), getGraphEdges()]).then(([nodesResult, edgesResult]) => {
      if (!active) {
        return;
      }

      setState({
        nodes: nodesResult.status === "fulfilled" ? nodesResult.value : null,
        edges: edgesResult.status === "fulfilled" ? edgesResult.value : null,
        loading: false,
        nodesError: nodesResult.status === "rejected" ? messageFor(nodesResult.reason) : null,
        edgesError: edgesResult.status === "rejected" ? messageFor(edgesResult.reason) : null
      });
    });

    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedNodeId) {
      setNeighborhood({ data: null, loading: false, error: null });
      return;
    }

    let active = true;
    setNeighborhood({ data: null, loading: true, error: null });

    getGraphNeighborhood(selectedNodeId, 1)
      .then((data) => {
        if (active) {
          setNeighborhood({ data, loading: false, error: null });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setNeighborhood({ data: null, loading: false, error: messageFor(error) });
        }
      });

    return () => {
      active = false;
    };
  }, [selectedNodeId]);

  return (
    <>
      <section className="page-heading" aria-labelledby="graph-title">
        <p className="hero__eyebrow">Deterministic graph extraction</p>
        <h1 className="page-heading__title" id="graph-title">
          Graph Explorer
        </h1>
        <p className="page-heading__subtitle">
          Read-only inspection of extracted graph nodes, relation evidence, source
          references, and selected node neighborhoods from local graph artifacts.
        </p>
      </section>

      {state.loading ? (
        <section className="section">
          <EmptyPanel title="Loading graph artifacts" description="Reading graph nodes and edges from the local API." />
        </section>
      ) : (
        <GraphContent
          state={state}
          selectedNodeId={selectedNodeId}
          onSelectedNodeIdChange={setSelectedNodeId}
          neighborhood={neighborhood}
        />
      )}
    </>
  );
}

function GraphContent({
  state,
  selectedNodeId,
  onSelectedNodeIdChange,
  neighborhood
}: {
  state: GraphExplorerState;
  selectedNodeId: string;
  onSelectedNodeIdChange: (nodeId: string) => void;
  neighborhood: NeighborhoodState;
}) {
  const nodes = state.nodes?.items ?? [];
  const edges = state.edges?.items ?? [];
  const nodeTypeBreakdown = useMemo(() => countBy(nodes, (node) => node.type), [nodes]);
  const relationTypeBreakdown = useMemo(() => countBy(edges, (edge) => edge.relation_type), [edges]);

  return (
    <>
      {state.nodesError || state.edgesError ? (
        <section className="section">
          <div className="inline-alert">
            {state.nodesError ? <p>GET /api/v1/graph/nodes?limit=200: {state.nodesError}</p> : null}
            {state.edgesError ? <p>GET /api/v1/graph/edges?limit=200: {state.edgesError}</p> : null}
          </div>
        </section>
      ) : null}

      <section className="section" aria-labelledby="graph-overview-title">
        <div className="section__header">
          <h2 className="section__title" id="graph-overview-title">
            Graph Overview
          </h2>
          <p className="section__note">Read-only graph API summary</p>
        </div>
        <div className="metric-grid">
          <MetricCard
            label="total graph nodes"
            value={formatNumber(state.nodes?.total)}
            detail={detailFor(state.nodes?.total)}
          />
          <MetricCard
            label="total graph edges"
            value={formatNumber(state.edges?.total)}
            detail={detailFor(state.edges?.total)}
          />
          <MetricCard
            label="node types"
            value={formatNumber(Object.keys(nodeTypeBreakdown).length)}
            detail={nodes.length > 0 ? "derived from displayed nodes" : "Unavailable"}
          />
          <MetricCard
            label="relation types"
            value={formatNumber(Object.keys(relationTypeBreakdown).length)}
            detail={edges.length > 0 ? "derived from displayed edges" : "Unavailable"}
          />
        </div>
      </section>

      <section className="section" aria-labelledby="graph-breakdowns-title">
        <div className="section__header">
          <h2 className="section__title" id="graph-breakdowns-title">
            Graph Breakdowns
          </h2>
          <p className="section__note">Counts derived from the first 200 returned records</p>
        </div>
        <div className="breakdown-grid">
          <BreakdownPanel title="node type breakdown" values={nodeTypeBreakdown} />
          <BreakdownPanel title="relation type breakdown" values={relationTypeBreakdown} />
        </div>
      </section>

      <section className="section" aria-labelledby="node-neighborhood-title">
        <div className="section__header">
          <h2 className="section__title" id="node-neighborhood-title">
            Selected Node Neighborhood
          </h2>
          <p className="section__note">GET /api/v1/graph/neighborhood?depth=1</p>
        </div>
        <NodeSelector nodes={nodes} selectedNodeId={selectedNodeId} onChange={onSelectedNodeIdChange} />
        <NeighborhoodPanel state={neighborhood} selectedNodeId={selectedNodeId} />
      </section>

      <section className="section" aria-labelledby="node-inventory-title">
        <div className="section__header">
          <h2 className="section__title" id="node-inventory-title">
            Graph Node Inventory
          </h2>
          <p className="section__note">{state.nodes ? `${state.nodes.total} total nodes, showing ${nodes.length}` : "nodes unavailable"}</p>
        </div>
        <NodeTable nodes={nodes} />
      </section>

      <section className="section" aria-labelledby="edge-inventory-title">
        <div className="section__header">
          <h2 className="section__title" id="edge-inventory-title">
            Graph Edge Evidence Inventory
          </h2>
          <p className="section__note">{state.edges ? `${state.edges.total} total edges, showing ${edges.length}` : "edges unavailable"}</p>
        </div>
        <EdgeTable edges={edges} />
      </section>
    </>
  );
}

function NodeSelector({
  nodes,
  selectedNodeId,
  onChange
}: {
  nodes: KnowledgeGraphNode[];
  selectedNodeId: string;
  onChange: (nodeId: string) => void;
}) {
  if (nodes.length === 0) {
    return <EmptyPanel title="No selectable nodes" description="Graph nodes are unavailable or the graph artifact is empty." />;
  }

  return (
    <div className="search-form graph-selector">
      <label className="search-form__label" htmlFor="graph-node-selector">
        node_id
      </label>
      <select
        className="search-form__input"
        id="graph-node-selector"
        value={selectedNodeId}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">No node selected</option>
        {nodes.map((node) => (
          <option value={node.node_id} key={node.node_id}>
            {node.node_id} - {node.label}
          </option>
        ))}
      </select>
    </div>
  );
}

function NeighborhoodPanel({
  state,
  selectedNodeId
}: {
  state: NeighborhoodState;
  selectedNodeId: string;
}) {
  if (!selectedNodeId) {
    return (
      <EmptyPanel
        title="No node selected"
        description="Select a node_id to inspect its depth-1 graph neighborhood."
      />
    );
  }

  if (state.loading) {
    return <EmptyPanel title="Loading neighborhood" description={`Reading depth-1 neighborhood for ${selectedNodeId}.`} />;
  }

  if (state.error) {
    return <EmptyPanel title="Neighborhood unavailable" description={state.error} tone="error" />;
  }

  if (!state.data) {
    return <EmptyPanel title="No neighborhood response" description="The graph API did not return neighborhood data." />;
  }

  return (
    <div className="evidence-viewer graph-neighborhood">
      <section className="evidence-column">
        <h3>selected_node</h3>
        <pre className="json-panel">{JSON.stringify(state.data.selected_node, null, 2)}</pre>
      </section>
      <section className="evidence-column">
        <h3>neighborhood nodes</h3>
        <pre className="json-panel">{JSON.stringify(state.data.nodes, null, 2)}</pre>
      </section>
      <section className="evidence-column evidence-column--wide">
        <h3>neighborhood edges</h3>
        <pre className="json-panel">{JSON.stringify(state.data.edges, null, 2)}</pre>
      </section>
    </div>
  );
}

function NodeTable({ nodes }: { nodes: KnowledgeGraphNode[] }) {
  if (nodes.length === 0) {
    return <EmptyPanel title="No graph nodes" description="No extracted graph nodes are currently visible." />;
  }

  return (
    <div className="table-shell">
      <table className="asset-table graph-table--nodes">
        <thead>
          <tr>
            <th>node_id</th>
            <th>label</th>
            <th>type</th>
            <th>mentions</th>
            <th>confidence</th>
            <th>source_doc_ids</th>
            <th>source_chunk_ids</th>
            <th>created_by</th>
          </tr>
        </thead>
        <tbody>
          {nodes.map((node) => (
            <tr key={node.node_id}>
              <td className="asset-table__id">{node.node_id}</td>
              <td>{node.label || "Unavailable"}</td>
              <td>{node.type || "Unavailable"}</td>
              <td>{formatList(node.mentions)}</td>
              <td>{formatConfidence(node.confidence)}</td>
              <td>{formatList(node.source_doc_ids)}</td>
              <td>{formatList(node.source_chunk_ids)}</td>
              <td>{node.created_by || "Unavailable"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EdgeTable({ edges }: { edges: KnowledgeGraphEdge[] }) {
  if (edges.length === 0) {
    return <EmptyPanel title="No graph edges" description="No extracted graph edge evidence is currently visible." />;
  }

  return (
    <div className="table-shell">
      <table className="asset-table graph-table--edges">
        <thead>
          <tr>
            <th>edge_id</th>
            <th>source_node_id</th>
            <th>target_node_id</th>
            <th>relation_type</th>
            <th>source_doc_id</th>
            <th>source_chunk_id</th>
            <th>evidence_quote</th>
            <th>confidence</th>
            <th>created_by</th>
          </tr>
        </thead>
        <tbody>
          {edges.map((edge) => (
            <tr key={edge.edge_id}>
              <td className="asset-table__id">{edge.edge_id}</td>
              <td className="asset-table__id">{edge.source_node_id}</td>
              <td className="asset-table__id">{edge.target_node_id}</td>
              <td>{edge.relation_type || "Unavailable"}</td>
              <td>{edge.source_doc_id || "Unavailable"}</td>
              <td>{edge.source_chunk_id || "Unavailable"}</td>
              <td className="graph-table__quote">{edge.evidence_quote || "Unavailable"}</td>
              <td>{formatConfidence(edge.confidence)}</td>
              <td>{edge.created_by || "Unavailable"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BreakdownPanel({ title, values }: { title: string; values: Record<string, number> }) {
  const entries = Object.entries(values).sort(([left], [right]) => left.localeCompare(right));

  return (
    <article className="breakdown-card">
      <div className="breakdown-card__header">
        <h3>{title}</h3>
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

function countBy<T>(items: T[], valueFor: (item: T) => string | null | undefined): Record<string, number> {
  return items.reduce<Record<string, number>>((counts, item) => {
    const value = valueFor(item) ?? "Unavailable";
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
  return value === null || value === undefined ? "Unavailable" : "from graph API";
}

function formatList(value: string[] | null | undefined): string {
  if (!value || value.length === 0) {
    return "Unavailable";
  }
  return value.join(", ");
}

function formatConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "Unavailable";
  }
  return value.toFixed(3);
}

function messageFor(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "API unavailable";
}
