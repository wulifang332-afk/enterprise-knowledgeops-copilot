from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx


class APIClientError(Exception):
    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


@dataclass
class KnowledgeOpsAPIClient:
    base_url: str = os.getenv("KNOWLEDGEOPS_API_URL", "http://localhost:8000")
    timeout_seconds: float = 30.0

    def ingest_all(self) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/v1/ingest",
            json={"ingest_all": True, "rebuild_indexes": True},
        )

    def documents(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", "/api/v1/documents", params=self._clean(params or {}))

    def chunks(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", "/api/v1/chunks", params=self._clean(params or {}))

    def search(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/search", json=payload)

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        try:
            response = httpx.request(method, url, timeout=self.timeout_seconds, **kwargs)
        except httpx.RequestError as exc:
            raise APIClientError(
                f"Could not reach KnowledgeOps API at {self.base_url}. Start FastAPI first.",
                {"error_code": "API_UNAVAILABLE", "request_id": "not-issued", "details": str(exc)},
            ) from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise APIClientError(
                "API returned a non-JSON response.",
                {"error_code": "INVALID_API_RESPONSE", "request_id": response.headers.get("X-Request-ID", "unknown")},
            ) from exc
        if response.status_code >= 400:
            raise APIClientError(payload.get("message", "API request failed."), payload)
        return payload

    @staticmethod
    def _clean(params: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in params.items() if value not in (None, "", [])}

