"""Pydantic v2 response models with camelCase aliases."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(w.capitalize() for w in parts[1:])


class _CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=_to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ── Agents ──────────────────────────────────────────────────────────


class AgentRunResponse(_CamelModel):
    agent_id: str
    run_id: str
    parent_agent_id: str | None = None
    task: str | None = None
    status: str = "running"
    total_turns: int = 0
    final_response: str | None = None
    child_count: int = 0
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ── Hypotheses ──────────────────────────────────────────────────────


class PipelineStepResponse(_CamelModel):
    id: int
    step_name: str
    status: str = "pending"
    confidence: dict[str, Any] | None = None
    runtime_seconds: float | None = None


class HypothesisResponse(_CamelModel):
    id: str
    protein_name: str | None = None
    ligand_name: str | None = None
    status: str = "pending"
    steps: list[PipelineStepResponse] = Field(default_factory=list)


# ── Artifacts ───────────────────────────────────────────────────────


class VizArtifactResponse(_CamelModel):
    id: int
    tool: str
    artifact_type: str
    file_path: str
    file_format: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Tool invocations ───────────────────────────────────────────────


class ToolInvocationResponse(_CamelModel):
    id: int
    tool: str
    subcommand: str | None = None
    status: str
    runtime_seconds: float | None = None
    inputs: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


# ── Runs ────────────────────────────────────────────────────────────


class RunCreateRequest(BaseModel):
    prompt: str


class RunCreateResponse(_CamelModel):
    run_id: str
    agent_id: str


class RunStatusResponse(_CamelModel):
    run_id: str
    agent_id: str
    status: str
    total_turns: int = 0
    final_response: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


# ── Stats ───────────────────────────────────────────────────────────


class StatsResponse(_CamelModel):
    agent_count: int = 0
    hypothesis_count: int = 0
    protein_count: int = 0
    ligand_count: int = 0
