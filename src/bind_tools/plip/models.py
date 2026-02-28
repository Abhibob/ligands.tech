"""Pydantic models for bind-plip, matching schemas/plip-request.schema.json and plip-result.schema.json."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


# ── Spec sub-models ──────────────────────────────────────────────────────────


class PlipOutputs(BaseModel):
    txt: bool = False
    xml: bool = False
    pymol: bool = False
    pics: bool = False

    model_config = {"populate_by_name": True}


class PlipStructureHandling(BaseModel):
    chains: list[str] = Field(default_factory=list)
    residues: list[str] = Field(default_factory=list)
    peptides: list[str] = Field(default_factory=list)
    intra: list[str] = Field(default_factory=list)
    no_hydro: bool = Field(False, alias="noHydro")
    keep_mod: bool = Field(False, alias="keepMod")
    no_fix: bool = Field(False, alias="noFix")

    model_config = {"populate_by_name": True}


class PlipProfileSpec(BaseModel):
    complex_path: str | None = Field(None, alias="complexPath")
    pdb_id: str | None = Field(None, alias="pdbId")
    binding_site: str | None = Field(None, alias="bindingSite")
    model: int = Field(1, ge=1)
    outputs: PlipOutputs = Field(default_factory=PlipOutputs)
    structure_handling: PlipStructureHandling = Field(
        default_factory=PlipStructureHandling, alias="structureHandling"
    )

    model_config = {"populate_by_name": True}


# ── Request ──────────────────────────────────────────────────────────────────


class PlipProfileRequest(BaseRequest):
    kind: str = "PlipProfileRequest"
    spec: PlipProfileSpec

    model_config = {"populate_by_name": True}


# ── Summary sub-models ───────────────────────────────────────────────────────


class PlipProfileSummary(BaseModel):
    binding_sites: list[str] = Field(default_factory=list, alias="bindingSites")
    selected_binding_site: str = Field("", alias="selectedBindingSite")
    interaction_counts: dict[str, int] = Field(
        default_factory=dict, alias="interactionCounts"
    )
    interacting_residues: list[str] = Field(
        default_factory=list, alias="interactingResidues"
    )
    interactions_by_type: dict[str, list[Any]] = Field(
        default_factory=dict, alias="interactionsByType"
    )

    model_config = {"populate_by_name": True}


# ── Result ───────────────────────────────────────────────────────────────────


class PlipProfileResult(BaseResult):
    kind: str = "PlipProfileResult"
    tool: str = "plip"
    summary: dict[str, Any] = Field(default_factory=dict)
