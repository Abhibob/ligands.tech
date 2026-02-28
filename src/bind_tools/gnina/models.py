"""Pydantic models for bind-gnina, matching schemas/gnina-request.schema.json and gnina-result.schema.json."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from bind_tools.common.envelope import BaseRequest, BaseResult


# ── Spec sub-models ──────────────────────────────────────────────────────────


class GninaLigand(BaseModel):
    id: str = ""
    smiles: str | None = None
    sdf_path: str | None = Field(None, alias="sdfPath")
    mol2_path: str | None = Field(None, alias="mol2Path")
    tags: list[str] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class GninaSearchSpace(BaseModel):
    autobox_ligand_path: str | None = Field(None, alias="autoboxLigandPath")
    center_x: float | None = Field(None, alias="centerX")
    center_y: float | None = Field(None, alias="centerY")
    center_z: float | None = Field(None, alias="centerZ")
    size_x: float | None = Field(None, alias="sizeX")
    size_y: float | None = Field(None, alias="sizeY")
    size_z: float | None = Field(None, alias="sizeZ")

    model_config = {"populate_by_name": True}


class GninaExecution(BaseModel):
    cnn_scoring: Literal["none", "rescore", "refinement", "all"] = Field(
        "rescore", alias="cnnScoring"
    )
    num_modes: int = Field(9, alias="numModes")
    exhaustiveness: int = 8
    seed: int | None = None
    cpu: int | None = None
    device: str | None = None
    no_gpu: bool = Field(False, alias="noGpu")
    pose_sort_order: Literal["cnnscore", "cnnaffinity", "energy"] = Field(
        "cnnscore", alias="poseSortOrder"
    )

    model_config = {"populate_by_name": True}


# ── Dock spec ────────────────────────────────────────────────────────────────


class GninaDockSpec(BaseModel):
    receptor_path: str = Field(..., alias="receptorPath")
    ligands: list[GninaLigand] = Field(default_factory=list)
    search_space: GninaSearchSpace = Field(
        default_factory=GninaSearchSpace, alias="searchSpace"
    )
    execution: GninaExecution = Field(default_factory=GninaExecution)
    scoring: Literal["vina", "vinardo", "ad4_scoring"] = "vina"

    model_config = {"populate_by_name": True}


class GninaDockRequest(BaseRequest):
    kind: str = "GninaDockRequest"
    spec: GninaDockSpec

    model_config = {"populate_by_name": True}


# ── Score spec ───────────────────────────────────────────────────────────────


class GninaScoreSpec(BaseModel):
    receptor_path: str = Field(..., alias="receptorPath")
    ligands: list[GninaLigand] = Field(default_factory=list)
    search_space: GninaSearchSpace = Field(
        default_factory=GninaSearchSpace, alias="searchSpace"
    )
    execution: GninaExecution = Field(default_factory=GninaExecution)

    model_config = {"populate_by_name": True}


class GninaScoreRequest(BaseRequest):
    kind: str = "GninaScoreRequest"
    spec: GninaScoreSpec

    model_config = {"populate_by_name": True}


# ── Minimize spec ────────────────────────────────────────────────────────────


class GninaMinimizeSpec(BaseModel):
    receptor_path: str = Field(..., alias="receptorPath")
    ligands: list[GninaLigand] = Field(default_factory=list)
    search_space: GninaSearchSpace = Field(
        default_factory=GninaSearchSpace, alias="searchSpace"
    )
    execution: GninaExecution = Field(default_factory=GninaExecution)
    minimize_iters: int = Field(0, alias="minimizeIters")

    model_config = {"populate_by_name": True}


class GninaMinimizeRequest(BaseRequest):
    kind: str = "GninaMinimizeRequest"
    spec: GninaMinimizeSpec

    model_config = {"populate_by_name": True}


# ── Result models ────────────────────────────────────────────────────────────


class GninaPose(BaseModel):
    rank: int = 0
    energy_kcal_mol: float = Field(0.0, alias="energyKcalMol")
    cnn_pose_score: float = Field(0.0, alias="cnnPoseScore")
    cnn_affinity: float = Field(0.0, alias="cnnAffinity")
    path: str = ""

    model_config = {"populate_by_name": True}


class GninaResultSummary(BaseModel):
    mode: str = ""
    num_poses: int = Field(0, alias="numPoses")
    pose_sort_order: str = Field("cnnscore", alias="poseSortOrder")
    top_pose: GninaPose | None = Field(None, alias="topPose")
    poses: list[GninaPose] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


class GninaResult(BaseResult):
    kind: str = "GninaResult"
    tool: str = "gnina"
    summary: dict[str, Any] = Field(default_factory=dict)
