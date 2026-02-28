"""Pydantic models for bind-ligprep ligand preparation."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


# ── Enums ────────────────────────────────────────────────────────────────────


class LigPrepEngine(str, Enum):
    auto = "auto"
    rdkit = "rdkit"
    obabel = "obabel"
    meeko = "meeko"


# ── Options ──────────────────────────────────────────────────────────────────


class LigPrepOptions(BaseModel):
    ph: float = Field(7.4, ge=0.0, le=14.0)
    enumerate_tautomers: bool = Field(False, alias="enumerateTautomers")
    enumerate_protomers: bool = Field(False, alias="enumerateProtomers")
    max_variants: int = Field(4, ge=1, alias="maxVariants")
    num_conformers: int = Field(1, ge=1, alias="numConformers")
    charge_model: str = Field("gasteiger", alias="chargeModel")
    output_formats: list[str] = Field(default_factory=lambda: ["sdf"], alias="outputFormats")
    engine: LigPrepEngine = Field(LigPrepEngine.auto)

    model_config = {"populate_by_name": True}


# ── Input ────────────────────────────────────────────────────────────────────


class LigPrepInput(BaseModel):
    smiles: str | None = None
    name: str | None = None
    pubchem_cid: int | None = Field(None, alias="pubchemCid")
    sdf_path: str | None = Field(None, alias="sdfPath")
    mol2_path: str | None = Field(None, alias="mol2Path")
    id: str = ""

    model_config = {"populate_by_name": True}


# ── Spec ─────────────────────────────────────────────────────────────────────


class LigPrepSpec(BaseModel):
    ligands: list[LigPrepInput] = Field(default_factory=list)
    manifest_path: str | None = Field(None, alias="manifestPath")
    protein_path: str | None = Field(None, alias="proteinPath")
    options: LigPrepOptions = Field(default_factory=LigPrepOptions)

    model_config = {"populate_by_name": True}


# ── Item result ──────────────────────────────────────────────────────────────


class LigPrepItemResult(BaseModel):
    id: str = ""
    input_query: str = Field("", alias="inputQuery")
    status: str = "succeeded"
    canonical_smiles: str | None = Field(None, alias="canonicalSmiles")
    net_charge: int | None = Field(None, alias="netCharge")
    rotatable_bonds: int | None = Field(None, alias="rotatableBonds")
    molecular_weight: float | None = Field(None, alias="molecularWeight")
    logp: float | None = None
    sdf_path: str | None = Field(None, alias="sdfPath")
    pdbqt_path: str | None = Field(None, alias="pdbqtPath")
    mol2_path: str | None = Field(None, alias="mol2Path")
    num_conformers: int = Field(0, alias="numConformers")
    tautomer_index: int = Field(0, alias="tautomerIndex")
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    runtime_seconds: float = Field(0.0, alias="runtimeSeconds")

    model_config = {"populate_by_name": True}


# ── Summary ──────────────────────────────────────────────────────────────────


class LigPrepSummary(BaseModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    items: list[LigPrepItemResult] = Field(default_factory=list)
    engine_used: str = Field("", alias="engineUsed")
    engine_version: str = Field("", alias="engineVersion")
    conversion_provenance: dict[str, str] = Field(
        default_factory=dict, alias="conversionProvenance"
    )

    model_config = {"populate_by_name": True}


# ── Request / Result ─────────────────────────────────────────────────────────


class LigPrepRequest(BaseRequest):
    kind: str = "LigPrepRequest"
    spec: LigPrepSpec

    model_config = {"populate_by_name": True}


class LigPrepResult(BaseResult):
    kind: str = "LigPrepResult"
    tool: str = "ligprep"
    summary: dict[str, Any] = Field(default_factory=dict)
