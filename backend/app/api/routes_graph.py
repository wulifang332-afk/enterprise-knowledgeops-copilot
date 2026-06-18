from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

from backend.app.api.dependencies import get_graph_service
from backend.app.api.utils import paginate, request_id_from
from backend.app.graph.service import GraphService
from backend.app.graph.schema import (
    GraphEdgeListResponse,
    GraphNeighborhoodResponse,
    GraphNodeListResponse,
    GraphRebuildResponse,
)

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.post("/rebuild", response_model=GraphRebuildResponse)
def rebuild_graph(
    request: Request,
    service: GraphService = Depends(get_graph_service),
) -> GraphRebuildResponse:
    result = service.rebuild()
    return GraphRebuildResponse(
        request_id=request_id_from(request),
        node_count=result.node_count,
        edge_count=result.edge_count,
        source_chunk_count=result.source_chunk_count,
        artifact_path=result.artifact_path,
    )


@router.get("/nodes", response_model=GraphNodeListResponse)
def graph_nodes(
    request: Request,
    type: str | None = Query(default=None),
    label_contains: str | None = Query(default=None),
    source_doc_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: GraphService = Depends(get_graph_service),
) -> GraphNodeListResponse:
    items = service.nodes(node_type=type, label_contains=label_contains, source_doc_id=source_doc_id)
    return GraphNodeListResponse(
        request_id=request_id_from(request),
        total=len(items),
        offset=offset,
        limit=limit,
        items=paginate(items, offset=offset, limit=limit),
    )


@router.get("/edges", response_model=GraphEdgeListResponse)
def graph_edges(
    request: Request,
    relation_type: str | None = Query(default=None),
    source_doc_id: str | None = Query(default=None),
    source_node_id: str | None = Query(default=None),
    target_node_id: str | None = Query(default=None),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    service: GraphService = Depends(get_graph_service),
) -> GraphEdgeListResponse:
    items = service.edges(
        relation_type=relation_type,
        source_doc_id=source_doc_id,
        source_node_id=source_node_id,
        target_node_id=target_node_id,
    )
    return GraphEdgeListResponse(
        request_id=request_id_from(request),
        total=len(items),
        offset=offset,
        limit=limit,
        items=paginate(items, offset=offset, limit=limit),
    )


@router.get("/neighborhood", response_model=GraphNeighborhoodResponse)
def graph_neighborhood(
    request: Request,
    node_id: str = Query(min_length=3),
    depth: int = Query(default=1, ge=1, le=2),
    service: GraphService = Depends(get_graph_service),
) -> GraphNeighborhoodResponse:
    selected_node, nodes, edges = service.neighborhood(node_id=node_id, depth=depth)
    return GraphNeighborhoodResponse(
        request_id=request_id_from(request),
        node_id=node_id,
        depth=depth,
        selected_node=selected_node,
        nodes=nodes,
        edges=edges,
    )
