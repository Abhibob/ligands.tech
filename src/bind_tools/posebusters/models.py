"""Pydantic models for bind-posebusters, matching schemas/posebusters-request.schema.json and posebusters-result.schema.json."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


class PoseBustersPerformance(BaseModel):
    top_n: int | None = Field(None, alias="topN")
    max_workers: int | None = Field(None, alias="maxWorkers")
    chunk_size: int | None = Field(None, alias="chunkSize")

    model_config = {"populate_by_name": True}


class PoseBustersCheckSpec(BaseModel):
    predicted_poses: list[str] = Field(..., alias="predictedPoses", min_length=1)
    protein_path: str | None = Field(None, alias="proteinPath")
    reference_ligand_path: str | None = Field(None, alias="referenceLigandPath")
    config: Literal["auto", "mol", "dock", "redock"] = "auto"
    full_report: bool = Field(False, alias="fullReport")
    performance: PoseBustersPerformance = Field(
        default_factory=PoseBustersPerformance, alias="performance"
    )

    model_config = {"populate_by_name": True}


class PoseBustersCheckRequest(BaseRequest):
    kind: str = "PoseBustersCheckRequest"
    spec: PoseBustersCheckSpec

    model_config = {"populate_by_name": True}


class PoseBustersPoseSummary(BaseModel):
    input_path: str = Field("", alias="inputPath")
    passes_all_checks: bool = Field(False, alias="passesAllChecks")
    pass_fraction: float = Field(0.0, alias="passFraction")
    fatal_failures: list[str] = Field(default_factory=list, alias="fatalFailures")
    major_failures: list[str] = Field(default_factory=list, alias="majorFailures")
    minor_failures: list[str] = Field(default_factory=list, alias="minorFailures")
    failed_checks: list[str] = Field(default_factory=list, alias="failedChecks")

    model_config = {"populate_by_name": True}


class PoseBustersCheckResult(BaseResult):
    kind: str = "PoseBustersCheckResult"
    tool: str = "posebusters"
    summary: dict[str, Any] = Field(default_factory=dict)
