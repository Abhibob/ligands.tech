"""Main ligand resolution pipeline orchestrator."""

import re
from pathlib import Path

from . import pubchem, rdkit_gen
from .models import LigandSearchInput, MolecularProperties, ResolvedLigand


async def resolve_ligand(inp: LigandSearchInput) -> ResolvedLigand:
    """
    Full resolution pipeline: name/SMILES/CID → PubChem → 3D SDF.

    This is the main function the orchestrator / agents call.
    """
    workspace = Path(inp.workspace_dir or "./workspace")
    ligand_dir = workspace / "ligands"
    ligand_dir.mkdir(parents=True, exist_ok=True)

    query = inp.query.strip()

    # Determine query type
    if query.upper().startswith("CID:"):
        # Direct PubChem CID
        cid = int(query[4:])
        compound = await pubchem.fetch_compound_by_cid(cid)

    elif _is_smiles(query):
        # SMILES string - try PubChem first, then RDKit
        cid = await pubchem.get_cid_by_smiles(query)
        if cid:
            compound = await pubchem.fetch_compound_by_cid(cid)
        else:
            # SMILES not in PubChem, use RDKit for 3D generation only
            compound = {"canonical_smiles": query}
            cid = None

    else:
        # Assume it's a compound name
        compound = await pubchem.search_by_name(query)
        if not compound:
            raise ValueError(
                f"Could not find ligand '{query}' in PubChem. "
                f"Try providing a SMILES string or PubChem CID."
            )
        cid = compound.get("cid")

    # Extract properties
    smiles = compound.get("canonical_smiles")
    isomeric_smiles = compound.get("isomeric_smiles")

    # Download/generate 3D structure
    sdf_3d_path = None
    sdf_2d_path = None

    if cid:
        # Try PubChem 3D first
        if inp.generate_3d:
            sdf_3d_path = await pubchem.download_sdf_3d(cid, ligand_dir)

        # Always get 2D
        sdf_2d_path = await pubchem.download_sdf_2d(cid, ligand_dir)

    # Fallback to RDKit if no 3D from PubChem
    if inp.generate_3d and not sdf_3d_path and smiles:
        if rdkit_gen.is_available():
            try:
                # Generate filename
                safe_name = _sanitize_filename(query)
                rdkit_path = ligand_dir / f"{safe_name}_rdkit_3d.sdf"
                sdf_3d_path = rdkit_gen.generate_3d_from_smiles(smiles, rdkit_path)
            except Exception:
                # RDKit generation failed, continue without 3D
                pass

    # Build molecular properties
    properties = None
    if compound:
        properties = MolecularProperties(
            molecular_weight=compound.get("molecular_weight"),
            molecular_formula=compound.get("molecular_formula"),
            logp=compound.get("logp"),
            tpsa=compound.get("tpsa"),
            h_bond_donors=compound.get("h_bond_donors"),
            h_bond_acceptors=compound.get("h_bond_acceptors"),
            rotatable_bonds=compound.get("rotatable_bonds"),
            heavy_atom_count=compound.get("heavy_atoms"),
            complexity=compound.get("complexity"),
            charge=compound.get("charge"),
        )

    # Extract name from synonyms
    name = None
    if compound and compound.get("synonyms"):
        # First synonym is usually the primary name
        name = compound["synonyms"][0]

    # Build result
    custom_id = f"ligand-{_sanitize_filename(name or query)}"

    return ResolvedLigand(
        query=query,
        name=name,
        pubchem_cid=cid,
        smiles=smiles,
        isomeric_smiles=isomeric_smiles,
        inchi=compound.get("inchi"),
        inchi_key=compound.get("inchi_key"),
        iupac_name=compound.get("iupac_name"),
        synonyms=compound.get("synonyms", [])[:10],  # Top 10
        sdf_2d_path=sdf_2d_path,
        sdf_3d_path=sdf_3d_path,
        properties=properties,
        custom_id=custom_id,
    )


def _is_smiles(query: str) -> bool:
    """
    Heuristic check if query is a SMILES string.

    SMILES strings typically contain:
    - Chemical symbols (C, N, O, etc.)
    - Bonds (=, #, -, etc.)
    - Rings (numbers)
    - Branches (parentheses)
    """
    # If it contains spaces or is very short, probably not SMILES
    if " " in query or len(query) < 3:
        return False

    # If it starts with common chemical prefixes, might be a name
    name_prefixes = ["acetyl", "methyl", "ethyl", "propyl", "amino", "hydroxy"]
    if any(query.lower().startswith(prefix) for prefix in name_prefixes):
        return False

    # SMILES characteristics
    smiles_chars = set("CNOPSFClBrI()[]=#-+@/\\\\0123456789cnops")
    query_chars = set(query)

    # If >80% of characters are SMILES-like, probably SMILES
    overlap = len(query_chars & smiles_chars)
    return overlap / len(query_chars) > 0.8


def _sanitize_filename(name: str) -> str:
    """Convert name to safe filename."""
    # Remove special characters, replace spaces with underscores
    safe = re.sub(r"[^\w\s-]", "", name.lower())
    safe = re.sub(r"[-\s]+", "_", safe)
    return safe[:50]  # Limit length
