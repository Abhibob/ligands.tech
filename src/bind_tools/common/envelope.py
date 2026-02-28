"""Base Pydantic models for the binding.dev/v1 request/result envelope."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_request_id() -> str:
    return f"req-{uuid4().hex[:12]}"


class Metadata(BaseModel):
    request_id: str = Field(default_factory=_new_request_id, alias="requestId")
    created_at: datetime = Field(default_factory=_now_utc, alias="createdAt")
    labels: dict[str, str] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


class BaseRequest(BaseModel):
    api_version: str = Field("binding.dev/v1", alias="apiVersion")
    kind: str
    metadata: Metadata = Field(default_factory=Metadata)

    model_config = {"populate_by_name": True}


class BaseResult(BaseModel):
    api_version: str = Field("binding.dev/v1", alias="apiVersion")
    kind: str
    metadata: Metadata = Field(default_factory=Metadata)
    tool: str = ""
    tool_version: str = Field("", alias="toolVersion")
    wrapper_version: str = Field("0.1.0", alias="wrapperVersion")
    status: str = "succeeded"  # succeeded | failed | partial
    inputs_resolved: dict[str, Any] = Field(default_factory=dict, alias="inputsResolved")
    parameters_resolved: dict[str, Any] = Field(
        default_factory=dict, alias="parametersResolved"
    )
    summary: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    runtime_seconds: float = Field(0.0, alias="runtimeSeconds")

    model_config = {"populate_by_name": True}

    def to_json(self, **kwargs: Any) -> str:
        return self.model_dump_json(by_alias=True, indent=2, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, mode="json")
