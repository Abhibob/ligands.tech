"""Memory runner — routes to Supermemory API or local fallback."""

from __future__ import annotations

import os
import time
from typing import Any

from .models import (
    MemoryAddResult,
    MemoryAddSpec,
    MemoryProfileResult,
    MemoryProfileSpec,
    MemorySearchResult,
    MemorySearchSpec,
)


def _get_client():
    """Return SupermemoryClient if API key is set, else LocalMemoryClient."""
    api_key = os.environ.get("SUPERMEMORY_API_KEY")
    if api_key:
        from .client import SupermemoryClient
        return SupermemoryClient(api_key)
    from .local_fallback import LocalMemoryClient
    return LocalMemoryClient()


def run_add(spec: MemoryAddSpec) -> MemoryAddResult:
    result = MemoryAddResult()
    result.inputs_resolved = {
        "containerTag": spec.container_tag,
        "customId": spec.custom_id,
        "contentLength": len(spec.content),
    }
    start = time.monotonic()
    try:
        client = _get_client()
        resp = client.add(spec)
        result.summary = resp
        result.status = "succeeded"
    except Exception as exc:
        result.status = "failed"
        result.errors.append(f"{type(exc).__name__}: {exc}")
    result.runtime_seconds = round(time.monotonic() - start, 3)
    return result


def run_search(spec: MemorySearchSpec) -> MemorySearchResult:
    result = MemorySearchResult()
    result.inputs_resolved = {
        "query": spec.query,
        "containerTag": spec.container_tag,
        "limit": spec.limit,
    }
    start = time.monotonic()
    try:
        client = _get_client()
        resp = client.search(spec)
        result.summary = resp
        result.status = "succeeded"
    except Exception as exc:
        result.status = "failed"
        result.errors.append(f"{type(exc).__name__}: {exc}")
    result.runtime_seconds = round(time.monotonic() - start, 3)
    return result


def run_profile(spec: MemoryProfileSpec) -> MemoryProfileResult:
    result = MemoryProfileResult()
    result.inputs_resolved = {
        "containerTag": spec.container_tag,
        "query": spec.query,
    }
    start = time.monotonic()
    try:
        client = _get_client()
        resp = client.profile(spec)
        result.summary = resp
        result.status = "succeeded"
    except Exception as exc:
        result.status = "failed"
        result.errors.append(f"{type(exc).__name__}: {exc}")
    result.runtime_seconds = round(time.monotonic() - start, 3)
    return result


def run_doctor() -> dict[str, Any]:
    """Check memory backend connectivity."""
    try:
        client = _get_client()
        return client.check_connectivity()
    except Exception as exc:
        return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
