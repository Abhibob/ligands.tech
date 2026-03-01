"""Pydantic data contracts for the memory module."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseResult


# ── Input specs ──────────────────────────────────────────────────────


class MemoryAddSpec(BaseModel):
    content: str
    container_tag: str = Field(..., alias="containerTag")
    custom_id: str | None = Field(None, alias="customId")
    metadata: dict[str, str | int | float | bool] | None = None
    entity_context: str | None = Field(None, alias="entityContext", max_length=1500)

    model_config = {"populate_by_name": True}


class MemorySearchSpec(BaseModel):
    query: str
    container_tag: str | None = Field(None, alias="containerTag")
    filters: dict | None = None
    limit: int = 10

    model_config = {"populate_by_name": True}


class MemoryProfileSpec(BaseModel):
    container_tag: str = Field(..., alias="containerTag")
    query: str | None = None

    model_config = {"populate_by_name": True}


# ── Result envelopes ─────────────────────────────────────────────────


class MemoryAddResult(BaseResult):
    kind: str = "MemoryAddResult"
    tool: str = "memory"


class MemorySearchResult(BaseResult):
    kind: str = "MemorySearchResult"
    tool: str = "memory"


class MemoryProfileResult(BaseResult):
    kind: str = "MemoryProfileResult"
    tool: str = "memory"
