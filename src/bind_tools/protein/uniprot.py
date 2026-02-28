"""UniProt REST API client for protein search and sequence retrieval."""

from __future__ import annotations

import re

import httpx

UNIPROT_BASE = "https://rest.uniprot.org"


async def search_uniprot(
    query: str,
    organism: str = "Homo sapiens",
) -> dict | None:
    """
    Search UniProt for a protein by name, gene, or accession.
    Returns the top reviewed (Swiss-Prot) hit as a dict, or None.

    The query syntax uses Solr-style field searches:
    - gene_exact:EGFR — exact gene name match
    - protein_name:epidermal — protein name search
    - accession:P00533 — direct accession lookup
    - organism_name:"Homo sapiens" — organism filter

    We try multiple strategies to get the best hit.
    """

    # Map organism common names to taxonomy IDs for precise filtering
    ORGANISM_TAX_IDS = {
        "Homo sapiens": "9606",
        "human": "9606",
        "Mus musculus": "10090",
        "mouse": "10090",
        "Rattus norvegicus": "10116",
        "rat": "10116",
        "Escherichia coli": "562",
    }

    tax_id = ORGANISM_TAX_IDS.get(organism, None)

    # Strategy 1: Try as a direct accession first (fast path)
    if _looks_like_accession(query):
        result = await _fetch_entry(query)
        if result:
            return result

    # Strategy 2: Exact gene name search (most common case)
    organism_clause = f" AND (taxonomy_id:{tax_id})" if tax_id else ""
    search_queries = [
        f"(gene_exact:{query}){organism_clause} AND (reviewed:true)",
        f"(protein_name:{query}){organism_clause} AND (reviewed:true)",
        f"(gene:{query}){organism_clause} AND (reviewed:true)",
        f"({query}){organism_clause}",  # full-text fallback
    ]

    for q in search_queries:
        result = await _search(q)
        if result:
            return result

    return None


async def _search(query: str) -> dict | None:
    """Execute a UniProt search and return the top hit."""
    url = f"{UNIPROT_BASE}/uniprotkb/search"
    params = {
        "query": query,
        "format": "json",
        "size": "1",
        "fields": (
            "accession,gene_names,protein_name,organism_name,"
            "organism_id,sequence,length,xref_pdb"
        ),
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        return None

    return _parse_uniprot_entry(results[0])


async def _fetch_entry(accession: str) -> dict | None:
    """Fetch a specific UniProt entry by accession."""
    url = f"{UNIPROT_BASE}/uniprotkb/{accession}.json"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()

    return _parse_uniprot_entry(data)


async def fetch_fasta(accession: str) -> str:
    """Fetch FASTA-formatted sequence for a UniProt accession."""
    url = f"{UNIPROT_BASE}/uniprotkb/{accession}.fasta"

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text


def _parse_uniprot_entry(entry: dict) -> dict:
    """Normalize a UniProt JSON entry into our fields."""

    # Gene name — UniProt nests this
    gene_name = ""
    genes = entry.get("genes", [])
    if genes:
        primary = genes[0].get("geneName", {})
        gene_name = primary.get("value", "")

    # Protein name
    protein_name = ""
    prot_desc = entry.get("proteinDescription", {})
    rec_name = prot_desc.get("recommendedName", {})
    if rec_name:
        protein_name = rec_name.get("fullName", {}).get("value", "")
    if not protein_name:
        sub_names = prot_desc.get("submissionNames", [])
        if sub_names:
            protein_name = sub_names[0].get("fullName", {}).get("value", "")

    # Organism
    organism = entry.get("organism", {}).get("scientificName", "")

    # Sequence
    seq_obj = entry.get("sequence", {})
    sequence = seq_obj.get("value", "")
    length = seq_obj.get("length", len(sequence))

    # PDB cross-references
    pdb_xrefs = []
    for xref in entry.get("uniProtKBCrossReferences", []):
        if xref.get("database") == "PDB":
            pdb_xrefs.append(xref.get("id", ""))

    return {
        "accession": entry.get("primaryAccession", ""),
        "gene_name": gene_name,
        "protein_name": protein_name,
        "organism": organism,
        "sequence": sequence,
        "length": length,
        "pdb_ids": pdb_xrefs,
    }


def _looks_like_accession(query: str) -> bool:
    """Check if query looks like a UniProt accession (e.g. P00533, Q9Y6K9)."""
    # Standard UniProt accession pattern
    return bool(
        re.match(r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$", query.upper())
        or re.match(r"^[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$", query.upper())
    )
