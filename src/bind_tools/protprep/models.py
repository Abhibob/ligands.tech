"""Pydantic models for bind-protprep protein structure preparation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


# ── Step toggles ──────────────────────────────────────────────────────────────


class ProtPrepSteps(BaseModel):
    add_hydrogens: bool = Field(True, alias="addHydrogens")
    fill_missing_residues: bool = Field(True, alias="fillMissingResidues")
    fill_missing_atoms: bool = Field(True, alias="fillMissingAtoms")
    remove_heterogens: bool = Field(True, alias="removeHeterogens")
    remove_water: bool = Field(True, alias="removeWater")
    replace_nonstandard: bool = Field(True, alias="replaceNonstandard")
    assign_protonation: bool = Field(True, alias="assignProtonation")
    energy_minimize: bool = Field(True, alias="energyMinimize")

    model_config = {"populate_by_name": True}


# ── Fine-grained options ─────────────────────────────────────────────────────


class ProtPrepOptions(BaseModel):
    ph: float = Field(7.4, ge=0.0, le=14.0)
    chains: list[str] = Field(default_factory=list)
    keep_water_within: float | None = Field(None, alias="keepWaterWithin")
    force_field: str = Field("amber14-all.xml", alias="forceField")
    water_model: str = Field("implicit", alias="waterModel")
    max_minimize_iterations: int = Field(500, ge=0, alias="maxMinimizeIterations")
    minimize_tolerance_kj: float = Field(10.0, gt=0.0, alias="minimizeToleranceKj")

    model_config = {"populate_by_name": True}


# ── Spec ──────────────────────────────────────────────────────────────────────


class ProtPrepSpec(BaseModel):
    input_path: str | None = Field(None, alias="inputPath")
    pdb_id: str | None = Field(None, alias="pdbId")
    output_format: str = Field("pdb", alias="outputFormat")
    steps: ProtPrepSteps = Field(default_factory=ProtPrepSteps)
    options: ProtPrepOptions = Field(default_factory=ProtPrepOptions)

    model_config = {"populate_by_name": True}


# ── Request ───────────────────────────────────────────────────────────────────


class ProtPrepRequest(BaseRequest):
    kind: str = "ProtPrepRequest"
    spec: ProtPrepSpec

    model_config = {"populate_by_name": True}


# ── Step result ───────────────────────────────────────────────────────────────


class ProtPrepStepResult(BaseModel):
    step: str
    applied: bool = False
    skipped_reason: str | None = Field(None, alias="skippedReason")
    details: str = ""
    count: int = 0

    model_config = {"populate_by_name": True}


# ── Summary ───────────────────────────────────────────────────────────────────


class ProtPrepSummary(BaseModel):
    hydrogens_added: int = Field(0, alias="hydrogensAdded")
    residues_filled: int = Field(0, alias="residuesFilled")
    atoms_filled: int = Field(0, alias="atomsFilled")
    heterogens_removed: int = Field(0, alias="heterogensRemoved")
    waters_removed: int = Field(0, alias="watersRemoved")
    nonstandard_replaced: int = Field(0, alias="nonstandardReplaced")
    chains_selected: list[str] = Field(default_factory=list, alias="chainsSelected")
    output_path: str = Field("", alias="outputPath")
    step_results: list[ProtPrepStepResult] = Field(
        default_factory=list, alias="stepResults"
    )

    model_config = {"populate_by_name": True}


# ── Result ────────────────────────────────────────────────────────────────────


class ProtPrepResult(BaseResult):
    kind: str = "ProtPrepResult"
    tool: str = "protprep"
    summary: dict[str, Any] = Field(default_factory=dict)
