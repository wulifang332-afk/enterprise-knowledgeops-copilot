from .routes_chunks import router as chunks_router
from .routes_documents import router as documents_router
from .routes_graph import router as graph_router
from .routes_ingest import router as ingest_router
from .routes_search import router as search_router

__all__ = ["chunks_router", "documents_router", "graph_router", "ingest_router", "search_router"]
