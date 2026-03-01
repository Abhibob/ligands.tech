"""Execution logic for bind-resolve: protein, ligand, and binder resolution.

Protein and ligand resolution is delegated to the richer ``bind_tools.protein``
and ``bind_tools.ligand`` modules.  Binder (ChEMBL) and RCSB structure search
remain implemented here with direct HTTP calls.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx

from bind_tools.common.errors import (
    InputMissingError,
    UpstreamError,
    ValidationError,
)
from bind_tools.common.runner import ensure_dir

logger = logging.getLogger(__name__)

# ── API base URLs (only those still used directly) ───────────────────────────

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"
CCD_BASE = "https://files.rcsb.org/ligands/download"

# ── Organism mapping ─────────────────────────────────────────────────────────

ORGANISM_MAP: dict[str, int] = {
    "human": 9606,
    "mouse": 10090,
    "rat": 10116,
    "ecoli": 562,
    "e.coli": 562,
    "yeast": 559292,
    "zebrafish": 7955,
    "drosophila": 7227,
    "chicken": 9031,
    "pig": 9823,
    "dog": 9615,
    "cow": 9913,
    "rabbit": 9986,
    "xenopus": 8364,
    "c.elegans": 6239,
    "arabidopsis": 3702,
}

# Common name → scientific name for the protein module (expects scientific names).
_ORGANISM_SCIENTIFIC: dict[str, str] = {
    "human": "Homo sapiens",
    "mouse": "Mus musculus",
    "rat": "Rattus norvegicus",
    "ecoli": "Escherichia coli",
    "e.coli": "Escherichia coli",
    "yeast": "Saccharomyces cerevisiae",
    "zebrafish": "Danio rerio",
    "drosophila": "Drosophila melanogaster",
    "chicken": "Gallus gallus",
    "pig": "Sus scrofa",
    "dog": "Canis lupus familiaris",
    "cow": "Bos taurus",
    "rabbit": "Oryctolagus cuniculus",
    "xenopus": "Xenopus tropicalis",
    "c.elegans": "Caenorhabditis elegans",
    "arabidopsis": "Arabidopsis thaliana",
}

# ── Shared HTTP client factory ───────────────────────────────────────────────

_DEFAULT_TIMEOUT = 30  # seconds


def _http_client() -> httpx.Client:
    """Return a pre-configured httpx client."""
    return httpx.Client(
        timeout=_DEFAULT_TIMEOUT,
        follow_redirects=True,
        headers={"Accept": "application/json"},
    )


def _get_json(client: httpx.Client, url: str, *, label: str = "API") -> Any:
    """Perform a GET and return parsed JSON, raising UpstreamError on failure."""
    logger.debug("GET %s", url)
    resp = client.get(url)
    if resp.status_code == 404:
        return None
    if resp.status_code != 200:
        raise UpstreamError(
            f"{label} returned HTTP {resp.status_code}: {resp.text[:300]}"
        )
    return resp.json()


def _download_file(client: httpx.Client, url: str, dest: Path, *, label: str = "file") -> Path:
    """Download a file from *url* to *dest*, returning the written path."""
    logger.debug("Downloading %s -> %s", url, dest)
    resp = client.get(url)
    if resp.status_code != 200:
        raise UpstreamError(
            f"Failed to download {label} (HTTP {resp.status_code}): {url}"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(resp.content)
    return dest


# ── Organism ID resolution helper ────────────────────────────────────────────


def _resolve_organism_id(organism: str | None, organism_id: int | None) -> int:
    """Return a numeric NCBI taxonomy ID from an organism name or explicit ID."""
    if organism_id is not None:
        return organism_id
    if organism is None:
        organism = "human"
    key = organism.lower().strip()
    if key in ORGANISM_MAP:
        return ORGANISM_MAP[key]
    # Attempt to parse as an integer directly
    try:
        return int(key)
    except ValueError:
        raise ValidationError(
            f"Unknown organism '{organism}'. Use one of: "
            f"{', '.join(sorted(ORGANISM_MAP.keys()))}, or pass --organism-id with a "
            "numeric NCBI taxonomy ID."
        )


# ══════════════════════════════════════════════════════════════════════════════
# resolve_protein  (delegates to bind_tools.protein)
# ══════════════════════════════════════════════════════════════════════════════


def _scientific_organism(organism: str | None) -> str:
    """Map a common organism name to the scientific name expected by the protein module."""
    if organism is None:
        return "Homo sapiens"
    key = organism.lower().strip()
    return _ORGANISM_SCIENTIFIC.get(key, organism)


def resolve_protein(
    name: str | None = None,
    organism: str | None = None,
    organism_id: int | None = None,
    uniprot_id: str | None = None,
    download_dir: str | None = None,
) -> dict[str, Any]:
    """Resolve a protein by gene name or UniProt accession.

    Delegates to ``bind_tools.protein.resolve_protein`` for the heavy lifting
    (UniProt search, PDB structure ranking, binding-site extraction, FASTA
    generation).  Results are mapped back to the summary dict expected by the
    resolve CLI.
    """
    if not name and not uniprot_id:
        raise InputMissingError(
            "Provide at least --name (gene name) or --uniprot (UniProt accession)."
        )

    try:
        from bind_tools.protein import (
            ProteinSearchInput,
            resolve_protein as _resolve_protein_async,
        )
    except Exception as exc:
        raise UpstreamError(
            f"bind_tools.protein module failed to load: {exc}"
        ) from exc

    query = uniprot_id.strip() if uniprot_id else (name or "")
    scientific = _scientific_organism(organism)

    inp = ProteinSearchInput(
        query=query,
        organism=scientific,
        download_best=download_dir is not None,
        workspace_dir=download_dir,
    )

    try:
        resolved = asyncio.run(_resolve_protein_async(inp))
    except ValueError as exc:
        raise UpstreamError(str(exc)) from exc

    # Map StructureHit list → legacy best_structures dicts
    best_structures: list[dict[str, Any]] = []
    for sh in resolved.structures:
        best_structures.append({
            "pdb_id": sh.pdb_id,
            "resolution": sh.resolution,
            "experimental_method": sh.method or "",
            "chain_id": sh.chains[0] if sh.chains else "",
            "has_ligand": sh.has_ligand,
            "ligand_ids": sh.ligand_ids,
        })

    # Determine downloaded path from best structure
    downloaded_path: str | None = None
    if resolved.best_structure:
        downloaded_path = resolved.best_structure.cif_path or resolved.best_structure.pdb_path

    # Binding sites
    binding_sites: list[dict[str, Any]] = []
    for bs in resolved.binding_sites:
        binding_sites.append({
            "site_id": bs.site_id,
            "residues": bs.residues,
            "ligand_id": bs.ligand_id,
            "ligand_name": bs.ligand_name,
            "source": bs.source,
        })

    return {
        "uniprot_accession": resolved.uniprot_id,
        "gene_name": resolved.gene_name,
        "protein_name": resolved.protein_name,
        "organism": resolved.organism,
        "sequence_length": resolved.sequence_length,
        "fasta_path": resolved.fasta_path,
        "best_structures": best_structures,
        "binding_sites": binding_sites,
        "downloaded_path": downloaded_path,
        "num_structures": len(best_structures),
    }


# ══════════════════════════════════════════════════════════════════════════════
# resolve_ligand  (delegates to bind_tools.ligand, except CCD path)
# ══════════════════════════════════════════════════════════════════════════════


def resolve_ligand(
    name: str | None = None,
    smiles: str | None = None,
    ccd: str | None = None,
    pubchem_cid: int | None = None,
    download_dir: str | None = None,
) -> dict[str, Any]:
    """Resolve a ligand from a name, SMILES, CCD code, or PubChem CID.

    The CCD path (RCSB Ligand Expo ideal SDF) is handled inline because the
    ligand module only supports PubChem.  All other paths delegate to
    ``bind_tools.ligand.resolve_ligand``.
    """
    if not any([name, smiles, ccd, pubchem_cid]):
        raise InputMissingError(
            "Provide at least one of --name, --smiles, --ccd, or --pubchem-cid."
        )

    # ── CCD path: kept inline (ligand module doesn't support CCD) ────────
    if ccd:
        ccd_upper = ccd.strip().upper()
        result: dict[str, Any] = {
            "source": "ccd",
            "identifier": ccd_upper,
            "smiles": "",
            "molecular_formula": "",
            "molecular_weight": None,
            "sdf_path": None,
        }
        if download_dir:
            dl_dir = ensure_dir(download_dir, label="download-dir", create=True)
            sdf_url = f"{CCD_BASE}/{ccd_upper}_ideal.sdf"
            dest = dl_dir / f"{ccd_upper}_ideal.sdf"
            with _http_client() as client:
                _download_file(client, sdf_url, dest, label="CCD SDF")
            result["sdf_path"] = str(dest)
        return result

    # ── All other paths: delegate to ligand module ───────────────────────
    if smiles:
        query = smiles
    elif pubchem_cid:
        query = f"CID:{pubchem_cid}"
    elif name:
        query = name
    else:
        raise InputMissingError("No ligand identifier provided.")

    try:
        from bind_tools.ligand import (
            LigandSearchInput,
            resolve_ligand as _resolve_ligand_async,
        )
    except Exception as exc:
        raise UpstreamError(
            f"bind_tools.ligand module failed to load: {exc}"
        ) from exc

    inp = LigandSearchInput(
        query=query,
        generate_3d=download_dir is not None,
        workspace_dir=download_dir,
    )

    try:
        resolved = asyncio.run(_resolve_ligand_async(inp))
    except ValueError as exc:
        raise UpstreamError(str(exc)) from exc

    # Map ResolvedLigand → summary dict
    props = resolved.properties
    result = {
        "source": "smiles" if smiles else ("pubchem_cid" if pubchem_cid else "pubchem_name"),
        "identifier": smiles or str(pubchem_cid or "") or name or "",
        "name": resolved.name or "",
        "smiles": resolved.smiles or resolved.isomeric_smiles or "",
        "iupac_name": resolved.iupac_name or "",
        "synonyms": resolved.synonyms,
        "pubchem_cid": resolved.pubchem_cid,
        "inchi_key": resolved.inchi_key or "",
        "molecular_formula": props.molecular_formula if props else "",
        "molecular_weight": props.molecular_weight if props else None,
        "logp": props.logp if props else None,
        "tpsa": props.tpsa if props else None,
        "h_bond_donors": props.h_bond_donors if props else None,
        "h_bond_acceptors": props.h_bond_acceptors if props else None,
        "rotatable_bonds": props.rotatable_bonds if props else None,
        "sdf_path": resolved.sdf_3d_path or resolved.sdf_2d_path,
    }
    return result


# ══════════════════════════════════════════════════════════════════════════════
# resolve_binders
# ══════════════════════════════════════════════════════════════════════════════


def resolve_binders(
    gene: str | None = None,
    organism_id: int | None = None,
    uniprot_id: str | None = None,
    min_pchembl: float = 6.0,
    limit: int = 20,
    download_dir: str | None = None,
) -> dict[str, Any]:
    """Resolve known binders and approved drugs for a protein target via ChEMBL.

    Steps:
      1. Resolve the protein to a UniProt accession (reuses resolve_protein).
      2. Map UniProt accession to ChEMBL target.
      3. Fetch bioactivity data filtered by pChEMBL value.
      4. Fetch mechanism-of-action / approved drug info.

    Returns a summary dict.
    """
    # Step 1: Resolve protein to get UniProt accession
    if uniprot_id:
        accession = uniprot_id.strip()
    elif gene:
        protein_info = resolve_protein(
            name=gene, organism_id=organism_id or 9606
        )
        accession = protein_info["uniprot_accession"]
    else:
        raise InputMissingError(
            "Provide at least --gene or --uniprot for binder resolution."
        )

    with _http_client() as client:
        # Step 2: UniProt -> ChEMBL target
        target_url = (
            f"{CHEMBL_BASE}/target.json"
            f"?target_components__accession={accession}&format=json"
        )
        target_data = _get_json(client, target_url, label="ChEMBL target")
        targets = (target_data or {}).get("targets", [])
        if not targets:
            return {
                "uniprot_accession": accession,
                "chembl_target_id": None,
                "message": "No ChEMBL target found for this accession.",
                "approved_drugs": [],
                "top_compounds": [],
            }

        target_chembl_id = targets[0].get("target_chembl_id", "")
        target_pref_name = targets[0].get("pref_name", "")

        # Step 3: Bioactivity data
        activity_url = (
            f"{CHEMBL_BASE}/activity.json"
            f"?target_chembl_id={target_chembl_id}"
            f"&pchembl_value__gte={min_pchembl}"
            f"&format=json&limit={limit}&order_by=-pchembl_value"
        )
        activity_data = _get_json(client, activity_url, label="ChEMBL activity")
        activities = (activity_data or {}).get("activities", [])

        top_compounds: list[dict[str, Any]] = []
        for act in activities:
            top_compounds.append(
                {
                    "molecule_chembl_id": act.get("molecule_chembl_id", ""),
                    "molecule_name": act.get("molecule_pref_name", ""),
                    "pchembl_value": act.get("pchembl_value"),
                    "standard_type": act.get("standard_type", ""),
                    "standard_value": act.get("standard_value"),
                    "standard_units": act.get("standard_units", ""),
                    "canonical_smiles": act.get("canonical_smiles", ""),
                }
            )

        # Step 4: Approved drugs via mechanism of action
        mechanism_url = (
            f"{CHEMBL_BASE}/mechanism.json"
            f"?target_chembl_id={target_chembl_id}&format=json"
        )
        mechanism_data = _get_json(client, mechanism_url, label="ChEMBL mechanism")
        mechanisms = (mechanism_data or {}).get("mechanisms", [])

        approved_drugs: list[dict[str, Any]] = []
        for mech in mechanisms:
            approved_drugs.append(
                {
                    "molecule_chembl_id": mech.get("molecule_chembl_id", ""),
                    "drug_name": mech.get("molecule_name", ""),
                    "mechanism_of_action": mech.get("mechanism_of_action", ""),
                    "action_type": mech.get("action_type", ""),
                    "max_phase": mech.get("max_phase"),
                }
            )

    return {
        "uniprot_accession": accession,
        "chembl_target_id": target_chembl_id,
        "target_name": target_pref_name,
        "num_approved_drugs": len(approved_drugs),
        "num_top_compounds": len(top_compounds),
        "approved_drugs": approved_drugs,
        "top_compounds": top_compounds,
    }


# ══════════════════════════════════════════════════════════════════════════════
# search_structures (RCSB PDB text search)
# ══════════════════════════════════════════════════════════════════════════════

RCSB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"


def search_structures(
    gene: str | None = None,
    organism: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Search the RCSB PDB for structures matching a gene name and organism.

    Uses the RCSB Search API v2 with a full-text query.

    Returns a summary dict with PDB IDs and basic metadata.
    """
    if not gene:
        raise InputMissingError("Provide --gene for structure search.")

    # Build a simple full-text query
    query_text = gene
    if organism:
        query_text = f"{gene} {organism}"

    search_payload = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": query_text},
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": limit},
            "results_content_type": ["experimental"],
            "sort": [{"sort_by": "score", "direction": "desc"}],
        },
    }

    with _http_client() as client:
        resp = client.post(
            RCSB_SEARCH_URL,
            json=search_payload,
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code != 200:
            raise UpstreamError(
                f"RCSB search returned HTTP {resp.status_code}: {resp.text[:300]}"
            )
        data = resp.json()

    result_set = data.get("result_set", [])
    pdb_ids = [entry.get("identifier", "") for entry in result_set]
    total_count = data.get("total_count", 0)

    return {
        "query": query_text,
        "total_count": total_count,
        "returned": len(pdb_ids),
        "pdb_ids": pdb_ids,
    }
