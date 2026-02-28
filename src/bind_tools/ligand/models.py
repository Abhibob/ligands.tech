"""Pydantic models for ligand resolution."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class MolecularProperties(BaseModel):
    """Calculated molecular properties."""

    molecular_weight: Optional[float] = None  # Daltons
    molecular_formula: Optional[str] = None  # "C22H23N3O4"
    logp: Optional[float] = None  # Lipophilicity
    tpsa: Optional[float] = None  # Topological polar surface area (Ų)
    h_bond_donors: Optional[int] = None
    h_bond_acceptors: Optional[int] = None
    rotatable_bonds: Optional[int] = None
    heavy_atom_count: Optional[int] = None
    complexity: Optional[float] = None
    charge: Optional[int] = None


class ResolvedLigand(BaseModel):
    """Complete resolved ligand — everything downstream tools need."""

    # What the user asked for
    query: str  # "erlotinib", "SMILES:...", "CID:176870"

    # Primary identifiers
    name: Optional[str] = None  # "Erlotinib"
    pubchem_cid: Optional[int] = None  # 176870
    chembl_id: Optional[str] = None  # "CHEMBL553"
    inchi_key: Optional[str] = None  # "AAKJLRGGTJKAMG-UHFFFAOYSA-N"

    # Chemical structure
    smiles: Optional[str] = None  # Canonical SMILES
    isomeric_smiles: Optional[str] = None  # With stereochemistry
    inchi: Optional[str] = None  # InChI string

    # 3D structure files
    sdf_2d_path: Optional[str] = None  # 2D SDF file path
    sdf_3d_path: Optional[str] = None  # 3D SDF file path (from PubChem or RDKit)

    # Molecular properties
    properties: Optional[MolecularProperties] = None

    # Drug/clinical data
    iupac_name: Optional[str] = None
    synonyms: list[str] = []
    max_clinical_phase: Optional[int] = None  # 0-4 (4 = approved)

    # For caching in supermemory
    custom_id: Optional[str] = None  # "ligand-erlotinib"


class LigandSearchInput(BaseModel):
    """What an agent passes to ligand_resolve."""

    query: str = Field(
        ...,
        description=(
            "Ligand name (e.g., 'erlotinib'), SMILES string, "
            "PubChem CID (e.g., 'CID:176870'), or 3-letter PDB code (e.g., 'AQ4')"
        ),
    )
    generate_3d: bool = Field(True, description="Generate 3D coordinates")
    workspace_dir: Optional[str] = None
