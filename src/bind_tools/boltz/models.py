"""Pydantic models for bind-boltz, matching schemas/boltz2-request.schema.json and boltz2-result.schema.json."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


# ── Target ──────────────────────────────────────────────────────────────────


class BoltzTarget(BaseModel):
    protein_fasta_path: str | None = Field(None, alias="proteinFastaPath")
    protein_sequence: str | None = Field(None, alias="proteinSequence")
    protein_pdb_path: str | None = Field(None, alias="proteinPdbPath")
    protein_cif_path: str | None = Field(None, alias="proteinCifPath")
    name: str | None = None

    model_config = {"populate_by_name": True}


# ── Ligand ──────────────────────────────────────────────────────────────────


class BoltzLigand(BaseModel):
    id: str | None = None
    smiles: str | None = None
    sdf_path: str | None = Field(None, alias="sdfPath")
    mol2_path: str | None = Field(None, alias="mol2Path")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


# ── MSA ─────────────────────────────────────────────────────────────────────


class BoltzMsa(BaseModel):
    use_server: bool = Field(False, alias="useServer")
    msa_dir: str | None = Field(None, alias="msaDir")

    model_config = {"populate_by_name": True}


# ── Constraints ─────────────────────────────────────────────────────────────


class BoltzConstraints(BaseModel):
    template_paths: list[str] = Field(default_factory=list, alias="templatePaths")
    pocket_residues: list[str] = Field(default_factory=list, alias="pocketResidues")
    contacts: list[str] = Field(default_factory=list)
    method_conditioning: list[str] = Field(default_factory=list, alias="methodConditioning")

    model_config = {"populate_by_name": True}


# ── Execution ───────────────────────────────────────────────────────────────


class BoltzExecution(BaseModel):
    rank_by: Literal["binder-probability", "affinity-value"] = Field(
        "binder-probability", alias="rankBy"
    )
    top_k: int = Field(1, ge=1, alias="topK")
    seed: int | None = None
    recycling_steps: int | None = Field(None, ge=0, alias="recyclingSteps")
    diffusion_samples: int | None = Field(None, ge=1, alias="diffusionSamples")
    device: str | None = None

    model_config = {"populate_by_name": True}


# ── Predict spec ────────────────────────────────────────────────────────────


class BoltzPredictSpec(BaseModel):
    target: BoltzTarget = Field(default_factory=BoltzTarget)
    ligands: list[BoltzLigand] = Field(default_factory=list)
    task: Literal["structure", "affinity", "both"] = "structure"
    msa: BoltzMsa = Field(default_factory=BoltzMsa)
    constraints: BoltzConstraints = Field(default_factory=BoltzConstraints)
    execution: BoltzExecution = Field(default_factory=BoltzExecution)

    model_config = {"populate_by_name": True}


# ── Request envelope ────────────────────────────────────────────────────────


class BoltzPredictRequest(BaseRequest):
    kind: str = "BoltzPredictRequest"
    spec: BoltzPredictSpec = Field(default_factory=BoltzPredictSpec)

    model_config = {"populate_by_name": True}


# ── Affinity sub-model ──────────────────────────────────────────────────────


class BoltzAffinity(BaseModel):
    binder_probability: float | None = Field(None, alias="binderProbability")
    affinity_value: float | None = Field(None, alias="affinityValue")
    affinity_unit: str | None = Field(None, alias="affinityUnit")

    model_config = {"populate_by_name": True}


# ── Result envelope ─────────────────────────────────────────────────────────


class BoltzPredictResult(BaseResult):
    kind: str = "BoltzPredictResult"
    tool: str = "boltz"
    summary: dict[str, Any] = Field(default_factory=dict)
