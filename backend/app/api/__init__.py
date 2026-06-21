from .routes_chunks import router as chunks_router
from .routes_documents import router as documents_router
from .routes_evaluation import router as evaluation_router
from .routes_feedback import router as feedback_router
from .routes_graph import router as graph_router
from .routes_ingest import router as ingest_router
from .routes_query import router as query_router
from .routes_search import router as search_router
from .routes_workspace import router as studio_router

__all__ = [
    "chunks_router",
    "documents_router",
    "evaluation_router",
    "feedback_router",
    "graph_router",
    "ingest_router",
    "query_router",
    "search_router",
    "studio_router",
]
