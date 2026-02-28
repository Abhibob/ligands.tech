"""Execution logic for bind-resolve: protein, ligand, and binder resolution
via public bioinformatics APIs (UniProt, PDBe, AlphaFold, RCSB, PubChem, ChEMBL).

All HTTP calls use ``httpx.Client`` with a 30-second timeout.
"""

from __future__ import annotations

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

# ── API base URLs ────────────────────────────────────────────────────────────

UNIPROT_BASE = "https://rest.uniprot.org"
PDBE_BASE = "https://www.ebi.ac.uk/pdbe"
ALPHAFOLD_BASE = "https://alphafold.ebi.ac.uk"
RCSB_BASE = "https://files.rcsb.org"
PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
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
# resolve_protein
# ══════════════════════════════════════════════════════════════════════════════


def resolve_protein(
    name: str | None = None,
    organism: str | None = None,
    organism_id: int | None = None,
    uniprot_id: str | None = None,
    download_dir: str | None = None,
) -> dict[str, Any]:
    """Resolve a protein by gene name or UniProt accession.

    Steps:
      1. Search UniProt (unless *uniprot_id* is provided directly).
      2. Fetch best experimental structures from PDBe.
      3. Fetch AlphaFold prediction URL.
      4. Optionally download the best PDB structure.

    Returns a summary dict suitable for embedding in a result envelope.
    """
    if not name and not uniprot_id:
        raise InputMissingError(
            "Provide at least --name (gene name) or --uniprot (UniProt accession)."
        )

    with _http_client() as client:
        # ── Step 1: Resolve UniProt accession ────────────────────────────
        accession: str
        protein_name: str = ""
        gene_name: str = name or ""
        organism_label: str = organism or "human"

        if uniprot_id:
            accession = uniprot_id.strip()
            # Fetch entry metadata
            entry = _get_json(
                client,
                f"{UNIPROT_BASE}/uniprotkb/{accession}.json",
                label="UniProt",
            )
            if entry:
                protein_name = entry.get("proteinDescription", {}).get(
                    "recommendedName", {}
                ).get("fullName", {}).get("value", "")
                genes = entry.get("genes", [])
                if genes:
                    gene_name = genes[0].get("geneName", {}).get("value", gene_name)
        else:
            tax_id = _resolve_organism_id(organism, organism_id)
            query = f"(gene:{name})+AND+(organism_id:{tax_id})+AND+(reviewed:true)"
            url = (
                f"{UNIPROT_BASE}/uniprotkb/search"
                f"?query={query}&format=json&size=5&fields=accession,gene_names,"
                f"protein_name,organism_name,length,sequence"
            )
            data = _get_json(client, url, label="UniProt search")
            results = (data or {}).get("results", [])
            if not results:
                raise UpstreamError(
                    f"No reviewed UniProt entry found for gene='{name}', "
                    f"organism_id={tax_id}."
                )

            top = results[0]
            accession = top["primaryAccession"]
            protein_name = top.get("proteinDescription", {}).get(
                "recommendedName", {}
            ).get("fullName", {}).get("value", "")
            genes = top.get("genes", [])
            if genes:
                gene_name = genes[0].get("geneName", {}).get("value", gene_name)
            organism_label = top.get("organism", {}).get("scientificName", organism_label)

        # ── Step 2: Best experimental structures (PDBe) ──────────────────
        best_structures: list[dict[str, Any]] = []
        pdbe_data = _get_json(
            client,
            f"{PDBE_BASE}/graph-api/mappings/best_structures/{accession}",
            label="PDBe best_structures",
        )
        if pdbe_data and accession in pdbe_data:
            for entry in pdbe_data[accession][:10]:
                best_structures.append(
                    {
                        "pdb_id": entry.get("pdb_id", ""),
                        "resolution": entry.get("resolution"),
                        "experimental_method": entry.get("experimental_method", ""),
                        "chain_id": entry.get("chain_id", ""),
                        "coverage": entry.get("coverage", 0),
                        "start": entry.get("start", 0),
                        "end": entry.get("end", 0),
                    }
                )

        # ── Step 3: AlphaFold prediction ─────────────────────────────────
        alphafold_url: str | None = None
        af_data = _get_json(
            client,
            f"{ALPHAFOLD_BASE}/api/prediction/{accession}",
            label="AlphaFold",
        )
        if af_data:
            # The AF API returns a list; take the first entry
            af_entries = af_data if isinstance(af_data, list) else [af_data]
            if af_entries:
                alphafold_url = af_entries[0].get("pdbUrl") or af_entries[0].get(
                    "cifUrl"
                )

        # ── Step 4: Optional download ────────────────────────────────────
        downloaded_path: str | None = None
        if download_dir and best_structures:
            dl_dir = ensure_dir(download_dir, label="download-dir", create=True)
            pdb_id = best_structures[0]["pdb_id"]
            dest = dl_dir / f"{pdb_id}.cif"
            download_url = f"{RCSB_BASE}/download/{pdb_id}.cif"
            try:
                _download_file(client, download_url, dest, label="PDB structure")
                downloaded_path = str(dest)
            except UpstreamError as exc:
                logger.warning("Download failed, trying .pdb: %s", exc)
                dest_pdb = dl_dir / f"{pdb_id}.pdb"
                download_url_pdb = f"{RCSB_BASE}/download/{pdb_id}.pdb"
                _download_file(client, download_url_pdb, dest_pdb, label="PDB structure")
                downloaded_path = str(dest_pdb)

    return {
        "uniprot_accession": accession,
        "gene_name": gene_name,
        "protein_name": protein_name,
        "organism": organism_label,
        "best_structures": best_structures,
        "alphafold_url": alphafold_url,
        "downloaded_path": downloaded_path,
        "num_structures": len(best_structures),
    }


# ══════════════════════════════════════════════════════════════════════════════
# resolve_ligand
# ══════════════════════════════════════════════════════════════════════════════


def resolve_ligand(
    name: str | None = None,
    smiles: str | None = None,
    ccd: str | None = None,
    pubchem_cid: int | None = None,
    download_dir: str | None = None,
) -> dict[str, Any]:
    """Resolve a ligand from a name, SMILES, CCD code, or PubChem CID.

    Priority order:
      1. *smiles* -- generate 3D SDF locally via RDKit.
      2. *ccd* -- download ideal SDF from RCSB CCD.
      3. *pubchem_cid* -- fetch from PubChem by CID.
      4. *name* -- search PubChem by compound name.

    Returns a summary dict.
    """
    if not any([name, smiles, ccd, pubchem_cid]):
        raise InputMissingError(
            "Provide at least one of --name, --smiles, --ccd, or --pubchem-cid."
        )

    dl_dir: Path | None = None
    if download_dir:
        dl_dir = ensure_dir(download_dir, label="download-dir", create=True)

    result: dict[str, Any] = {
        "source": "",
        "identifier": "",
        "smiles": smiles or "",
        "molecular_formula": "",
        "molecular_weight": None,
        "sdf_path": None,
    }

    # ── Path 1: SMILES via RDKit ─────────────────────────────────────────
    if smiles:
        result["source"] = "smiles"
        result["identifier"] = smiles
        if dl_dir:
            sdf_path = dl_dir / "ligand_from_smiles.sdf"
            _generate_sdf_from_smiles(smiles, sdf_path)
            result["sdf_path"] = str(sdf_path)
        return result

    with _http_client() as client:
        # ── Path 2: CCD (RCSB ligand) ───────────────────────────────────
        if ccd:
            ccd_upper = ccd.strip().upper()
            result["source"] = "ccd"
            result["identifier"] = ccd_upper
            sdf_url = f"{CCD_BASE}/{ccd_upper}_ideal.sdf"

            if dl_dir:
                dest = dl_dir / f"{ccd_upper}_ideal.sdf"
                _download_file(client, sdf_url, dest, label="CCD SDF")
                result["sdf_path"] = str(dest)
            return result

        # ── Path 3: PubChem by CID ──────────────────────────────────────
        if pubchem_cid:
            result["source"] = "pubchem_cid"
            result["identifier"] = str(pubchem_cid)
            _fill_pubchem(client, result, f"compound/cid/{pubchem_cid}", dl_dir)
            return result

        # ── Path 4: PubChem by name ─────────────────────────────────────
        if name:
            result["source"] = "pubchem_name"
            result["identifier"] = name
            _fill_pubchem(client, result, f"compound/name/{name}", dl_dir)
            return result

    return result


def _fill_pubchem(
    client: httpx.Client,
    result: dict[str, Any],
    path_segment: str,
    dl_dir: Path | None,
) -> None:
    """Fetch property info and 3D SDF from PubChem, mutating *result* in-place."""
    # Properties
    prop_url = (
        f"{PUBCHEM_BASE}/{path_segment}"
        "/property/IsomericSMILES,MolecularFormula,MolecularWeight/JSON"
    )
    prop_data = _get_json(client, prop_url, label="PubChem properties")
    if prop_data:
        props_list = (
            prop_data.get("PropertyTable", {}).get("Properties", [])
        )
        if props_list:
            p = props_list[0]
            result["smiles"] = p.get("IsomericSMILES", result["smiles"])
            result["molecular_formula"] = p.get("MolecularFormula", "")
            result["molecular_weight"] = p.get("MolecularWeight")
            result["pubchem_cid"] = p.get("CID")

    # 3D SDF download
    if dl_dir:
        sdf_url = f"{PUBCHEM_BASE}/{path_segment}/record/SDF?record_type=3d"
        identifier = result.get("identifier", "ligand")
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(identifier))
        dest = dl_dir / f"{safe_name}_pubchem.sdf"
        try:
            resp = client.get(sdf_url)
            if resp.status_code == 200:
                dest.write_bytes(resp.content)
                result["sdf_path"] = str(dest)
            else:
                logger.warning(
                    "PubChem 3D SDF not available (HTTP %d), skipping download.",
                    resp.status_code,
                )
        except httpx.HTTPError as exc:
            logger.warning("PubChem 3D SDF download failed: %s", exc)


def _generate_sdf_from_smiles(smiles: str, dest: Path) -> None:
    """Use RDKit to embed a 3D conformer and write an SDF file."""
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        raise InputMissingError(
            "RDKit is required to generate 3D SDF from SMILES. "
            "Install it with: pip install rdkit-pypi"
        )

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValidationError(f"RDKit could not parse SMILES: {smiles}")

    mol = Chem.AddHs(mol)
    status = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if status != 0:
        raise UpstreamError(
            f"RDKit 3D embedding failed for SMILES: {smiles} (status={status})"
        )
    AllChem.MMFFOptimizeMolecule(mol)

    dest.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(dest))
    writer.write(mol)
    writer.close()


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
