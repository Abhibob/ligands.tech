"""PubChem PUG-REST API client for ligand search and retrieval."""

import asyncio
from pathlib import Path

import httpx

PUBCHEM_BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


async def search_by_name(name: str) -> dict | None:
    """
    Search PubChem by compound name.
    Returns compound data or None if not found.
    """
    # Get CID first
    cid = await get_cid_by_name(name)
    if not cid:
        return None

    # Fetch full compound data
    return await fetch_compound_by_cid(cid)


async def get_cid_by_name(name: str) -> int | None:
    """Get PubChem CID (Compound ID) from name."""
    url = f"{PUBCHEM_BASE}/compound/name/{name}/cids/JSON"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        cids = data.get("IdentifierList", {}).get("CID", [])
        return cids[0] if cids else None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


async def get_cid_by_smiles(smiles: str) -> int | None:
    """Get PubChem CID from SMILES string."""
    url = f"{PUBCHEM_BASE}/compound/smiles/{smiles}/cids/JSON"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=30)
            resp.raise_for_status()
            data = resp.json()

        cids = data.get("IdentifierList", {}).get("CID", [])
        return cids[0] if cids else None

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return None
        raise


async def fetch_compound_by_cid(cid: int) -> dict:
    """
    Fetch complete compound data from PubChem by CID.
    Returns dict with properties, identifiers, etc.
    """
    # Fetch properties
    properties_url = (
        f"{PUBCHEM_BASE}/compound/cid/{cid}/property/"
        f"IsomericSMILES,CanonicalSMILES,MolecularFormula,MolecularWeight,"
        f"InChI,InChIKey,IUPACName,XLogP,TPSA,Complexity,Charge,"
        f"HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount/JSON"
    )

    # Fetch synonyms
    synonyms_url = f"{PUBCHEM_BASE}/compound/cid/{cid}/synonyms/JSON"

    async with httpx.AsyncClient() as client:
        # Fetch in parallel
        props_task = client.get(properties_url, timeout=30)
        syns_task = client.get(synonyms_url, timeout=30)

        props_resp, syns_resp = await asyncio.gather(props_task, syns_task)

        props_resp.raise_for_status()
        props_data = props_resp.json()

        # Synonyms might fail (not critical)
        synonyms = []
        if syns_resp.status_code == 200:
            syns_data = syns_resp.json()
            info = syns_data.get("InformationList", {}).get("Information", [])
            if info:
                synonyms = info[0].get("Synonym", [])[:10]  # Top 10 synonyms

    properties = props_data.get("PropertyTable", {}).get("Properties", [])
    if not properties:
        raise ValueError(f"No properties found for CID {cid}")

    prop = properties[0]

    return {
        "cid": cid,
        "canonical_smiles": prop.get("CanonicalSMILES"),
        "isomeric_smiles": prop.get("IsomericSMILES"),
        "molecular_formula": prop.get("MolecularFormula"),
        "molecular_weight": prop.get("MolecularWeight"),
        "inchi": prop.get("InChI"),
        "inchi_key": prop.get("InChIKey"),
        "iupac_name": prop.get("IUPACName"),
        "logp": prop.get("XLogP"),
        "tpsa": prop.get("TPSA"),
        "complexity": prop.get("Complexity"),
        "charge": prop.get("Charge"),
        "h_bond_donors": prop.get("HBondDonorCount"),
        "h_bond_acceptors": prop.get("HBondAcceptorCount"),
        "rotatable_bonds": prop.get("RotatableBondCount"),
        "heavy_atoms": prop.get("HeavyAtomCount"),
        "synonyms": synonyms,
    }


async def download_sdf_2d(cid: int, output_dir: str | Path) -> str:
    """Download 2D SDF file from PubChem."""
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/record/SDF"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"pubchem_{cid}_2d.sdf"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=60, follow_redirects=True)
        resp.raise_for_status()
        filepath.write_bytes(resp.content)

    return str(filepath)


async def download_sdf_3d(cid: int, output_dir: str | Path) -> str | None:
    """
    Download 3D SDF file from PubChem (if available).
    Returns None if 3D conformer doesn't exist.
    """
    url = f"{PUBCHEM_BASE}/compound/cid/{cid}/record/SDF?record_type=3d"

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"pubchem_{cid}_3d.sdf"

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, timeout=60, follow_redirects=True)
            resp.raise_for_status()
            filepath.write_bytes(resp.content)

        return str(filepath)

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            # No 3D conformer available
            return None
        raise
