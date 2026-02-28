"""Pydantic models for bind-resolve, the identifier resolution wrapper."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from bind_tools.common.envelope import BaseResult


# ── Result models ────────────────────────────────────────────────────────────


class ResolveProteinResult(BaseResult):
    """Result envelope for protein resolution (UniProt + PDB + AlphaFold)."""

    kind: str = "ResolveProteinResult"
    tool: str = "resolve"
    summary: dict[str, Any] = Field(default_factory=dict)


class ResolveLigandResult(BaseResult):
    """Result envelope for ligand resolution (PubChem / CCD / SMILES)."""

    kind: str = "ResolveLigandResult"
    tool: str = "resolve"
    summary: dict[str, Any] = Field(default_factory=dict)


class ResolveBindersResult(BaseResult):
    """Result envelope for binder/drug resolution (ChEMBL)."""

    kind: str = "ResolveBindersResult"
    tool: str = "resolve"
    summary: dict[str, Any] = Field(default_factory=dict)
