"""RCSB PDB data fetching, binding site extraction, and structure ranking."""

from collections import defaultdict
from pathlib import Path

import httpx

from .models import BindingSite, StructureHit

RCSB_DATA_BASE = "https://data.rcsb.org/rest/v1/core"
RCSB_FILES_BASE = "https://files.rcsb.org/download"


async def fetch_structure_details(pdb_id: str) -> StructureHit:
    """
    Fetch metadata for a single PDB structure.
    Uses the RCSB Data REST API.
    """
    async with httpx.AsyncClient() as client:
        # Entry-level data (resolution, method, title)
        resp = await client.get(
            f"{RCSB_DATA_BASE}/entry/{pdb_id}",
            timeout=30,
        )
        resp.raise_for_status()
        entry = resp.json()

    # Resolution — from different places depending on method
    resolution = None
    refine = entry.get("rcsb_entry_info", {})
    resolution = refine.get("resolution_combined", [None])[0]

    # Experimental method
    method = None
    exptl = entry.get("exptl", [])
    if exptl:
        method = exptl[0].get("method", "")

    # Title
    title = entry.get("struct", {}).get("title", "")

    # Release date
    release_date = entry.get("rcsb_accession_info", {}).get("initial_release_date", "")

    # Fetch non-polymer entities (ligands) via per-entity endpoint
    ligand_ids = []
    has_ligand = False
    np_entity_ids = entry.get("rcsb_entry_container_identifiers", {}).get(
        "non_polymer_entity_ids", []
    )
    if np_entity_ids:
        try:
            async with httpx.AsyncClient() as client2:
                for eid in np_entity_ids:
                    resp2 = await client2.get(
                        f"{RCSB_DATA_BASE}/nonpolymer_entity/{pdb_id}/{eid}",
                        timeout=15,
                    )
                    if resp2.status_code == 200:
                        np_data = resp2.json()
                        comp_id = np_data.get("pdbx_entity_nonpoly", {}).get("comp_id", "")
                        if comp_id and comp_id not in _COMMON_ADDITIVES:
                            ligand_ids.append(comp_id)
                            has_ligand = True
        except Exception:
            pass

    return StructureHit(
        pdb_id=pdb_id,
        title=title,
        resolution=resolution,
        method=method,
        has_ligand=has_ligand,
        ligand_ids=ligand_ids,
        release_date=release_date,
    )


RCSB_GRAPHQL = "https://data.rcsb.org/graphql"

_BINDING_SITE_QUERY = """
query ($pdb_id: String!) {
  entry(entry_id: $pdb_id) {
    rcsb_binding_affinity {
      comp_id
      value
      type
      unit
    }
    nonpolymer_entities {
      pdbx_entity_nonpoly {
        comp_id
        name
      }
    }
  }
}
"""


async def fetch_binding_sites(pdb_id: str) -> list[BindingSite]:
    """Fetch binding site annotations from RCSB via the GraphQL API.

    Generates a BindingSite record for each unique non-additive ligand found
    in the structure, using ``rcsb_binding_affinity`` and the nonpolymer
    entity data.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            RCSB_GRAPHQL,
            json={"query": _BINDING_SITE_QUERY, "variables": {"pdb_id": pdb_id}},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()

    entry = (data.get("data") or {}).get("entry") or {}

    # Build a comp_id → name map from nonpolymer entities
    comp_names: dict[str, str] = {}
    for npe in entry.get("nonpolymer_entities") or []:
        pnp = npe.get("pdbx_entity_nonpoly") or {}
        cid = pnp.get("comp_id", "")
        if cid and cid not in _COMMON_ADDITIVES:
            comp_names[cid] = pnp.get("name") or ""

    # Collect unique ligand comp_ids from binding affinity records
    seen: set[str] = set()
    for ba in entry.get("rcsb_binding_affinity") or []:
        cid = ba.get("comp_id", "")
        if cid and cid not in _COMMON_ADDITIVES:
            seen.add(cid)

    # Also include ligands not in binding_affinity but present as nonpolymers
    seen.update(comp_names.keys())

    sites: list[BindingSite] = []
    for i, comp_id in enumerate(sorted(seen), start=1):
        sites.append(
            BindingSite(
                site_id=f"site_{i}",
                residues=[],
                ligand_id=comp_id,
                ligand_name=comp_names.get(comp_id),
                source="PDB",
            )
        )

    return sites


async def download_structure(
    pdb_id: str,
    output_dir: str | Path,
    format: str = "pdb",
) -> str:
    """
    Download a PDB structure file.

    format: "pdb" for .pdb, "cif" for .cif (mmCIF)
    Returns the path to the downloaded file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pdb_id_lower = pdb_id.lower()

    if format == "cif":
        url = f"{RCSB_FILES_BASE}/{pdb_id_lower}.cif"
        filename = f"{pdb_id_lower}.cif"
    else:
        url = f"{RCSB_FILES_BASE}/{pdb_id_lower}.pdb"
        filename = f"{pdb_id_lower}.pdb"

    filepath = output_dir / filename

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        filepath.write_bytes(resp.content)

    return str(filepath)


def rank_structures(structures: list[StructureHit]) -> list[StructureHit]:
    """
    Rank structures by suitability for docking/binding analysis.

    Heuristics (in priority order):
    1. Has a bound ligand (essential for reference pocket / autobox)
    2. X-ray diffraction (more reliable coordinates for docking)
    3. Higher resolution (lower Å number)
    4. More recent (likely better refinement)
    """

    def score(s: StructureHit) -> tuple:
        has_lig = 1 if s.has_ligand else 0
        is_xray = 1 if s.method and "X-RAY" in s.method.upper() else 0
        # Invert resolution so lower Å = higher score
        # Use 99 as fallback for missing resolution
        res = -(s.resolution if s.resolution else 99.0)
        date = s.release_date or "0000"
        return (has_lig, is_xray, res, date)

    return sorted(structures, key=score, reverse=True)


# Common crystallization additives / buffers to filter out
_COMMON_ADDITIVES = {
    "HOH",
    "SO4",
    "PO4",
    "GOL",
    "EDO",
    "ACT",
    "CL",
    "NA",
    "MG",
    "ZN",
    "CA",
    "K",
    "MN",
    "FE",
    "NI",
    "CO",
    "CU",
    "CD",
    "IOD",
    "BR",
    "FMT",
    "NO3",
    "SCN",
    "DMS",
    "MPD",
    "PEG",
    "PGE",
    "1PE",
    "P6G",
    "TRS",
    "CIT",
    "MES",
    "HED",
    "BME",
    "EPE",
    "IMD",
}
