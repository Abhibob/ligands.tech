"""Pydantic models for protein resolution."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class BindingSite(BaseModel):
    """A known binding pocket on the protein."""

    site_id: str  # e.g. "AC1" or "binding_site_1"
    residues: list[str]  # ["A:745", "A:793", "A:855"]
    ligand_id: Optional[str] = None  # 3-letter PDB ligand code, e.g. "AQ4"
    ligand_name: Optional[str] = None  # human-readable, e.g. "erlotinib"
    source: str = "PDB"  # "PDB", "UniProt", "user"


class StructureHit(BaseModel):
    """A PDB structure matching the protein query."""

    pdb_id: str  # "1M17"
    title: Optional[str] = None
    resolution: Optional[float] = None  # Å — lower is better
    method: Optional[str] = None  # "X-RAY DIFFRACTION", "ELECTRON MICROSCOPY"
    has_ligand: bool = False
    ligand_ids: list[str] = []  # ["AQ4", "ANP"]
    chains: list[str] = []  # ["A", "B"]
    release_date: Optional[str] = None

    # Populated after download
    pdb_path: Optional[str] = None  # local path to downloaded file
    cif_path: Optional[str] = None

    # Binding sites from this structure
    binding_sites: list[BindingSite] = []


class ResolvedProtein(BaseModel):
    """Complete resolved protein — everything downstream tools need."""

    # What the user asked for
    query: str  # "EGFR", "P00533", "epidermal growth factor receptor"

    # UniProt resolution
    uniprot_id: str  # "P00533"
    gene_name: str  # "EGFR"
    protein_name: str  # "Epidermal growth factor receptor"
    organism: str  # "Homo sapiens"
    sequence: str  # full canonical amino acid sequence
    sequence_length: int

    # FASTA file written to workspace
    fasta_path: Optional[str] = None

    # PDB structures, ranked by suitability for docking
    structures: list[StructureHit] = []
    best_structure: Optional[StructureHit] = None

    # Aggregated binding sites across all structures
    binding_sites: list[BindingSite] = []

    # For caching in supermemory
    custom_id: Optional[str] = None  # "protein-EGFR" for supermemory


class ProteinSearchInput(BaseModel):
    """What an agent passes to protein_resolve."""

    query: str = Field(..., description="Protein name, gene name, or UniProt ID")
    organism: str = Field("Homo sapiens", description="Target organism")
    max_structures: int = Field(5, description="Max PDB structures to return")
    download_best: bool = Field(True, description="Download the best structure file")
    workspace_dir: Optional[str] = None
