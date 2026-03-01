"""Supermemory HTTP client (sync httpx)."""

from __future__ import annotations

from typing import Any

import httpx

from .models import MemoryAddSpec, MemoryProfileSpec, MemorySearchSpec


class SupermemoryClient:
    """Thin wrapper around the Supermemory REST API."""

    BASE = "https://api.supermemory.ai"

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._http = httpx.Client(
            base_url=self.BASE,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    # ── add ───────────────────────────────────────────────────────────

    def add(self, spec: MemoryAddSpec) -> dict[str, Any]:
        """POST /v3/documents — store a document."""
        body: dict[str, Any] = {
            "content": spec.content,
            "containerTag": spec.container_tag,
        }
        if spec.custom_id:
            body["customId"] = spec.custom_id
        if spec.metadata:
            body["metadata"] = spec.metadata
        if spec.entity_context:
            body["entityContext"] = spec.entity_context

        resp = self._http.post("/v3/documents", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── search ────────────────────────────────────────────────────────

    def search(self, spec: MemorySearchSpec) -> dict[str, Any]:
        """POST /v3/search — semantic search."""
        body: dict[str, Any] = {"q": spec.query}
        if spec.container_tag:
            body["containerTags"] = [spec.container_tag]
        if spec.filters:
            body["filters"] = spec.filters

        resp = self._http.post("/v3/search", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── profile ───────────────────────────────────────────────────────

    def profile(self, spec: MemoryProfileSpec) -> dict[str, Any]:
        """POST /v4/profile — generate a profile summary for a container."""
        body: dict[str, Any] = {"containerTag": spec.container_tag}
        if spec.query:
            body["q"] = spec.query

        resp = self._http.post("/v4/profile", json=body)
        resp.raise_for_status()
        return resp.json()

    # ── doctor ────────────────────────────────────────────────────────

    def check_connectivity(self) -> dict[str, Any]:
        """Verify the API key works with a lightweight search."""
        resp = self._http.post("/v3/search", json={"q": "health check"})
        resp.raise_for_status()
        return {"status": "ok", "backend": "supermemory"}
