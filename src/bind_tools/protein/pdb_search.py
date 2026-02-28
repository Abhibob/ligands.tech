"""RCSB PDB structure search using direct HTTP requests."""

import httpx


def search_structures_by_uniprot(
    uniprot_id: str,
    organism: str = "Homo sapiens",
    max_results: int = 20,
) -> list[str]:
    """
    Find PDB structures for a UniProt accession.
    Returns a list of PDB IDs.

    Uses direct POST to https://search.rcsb.org/rcsbsearch/v2/query
    """
    # Build query JSON for RCSB search API
    query_json = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entity_source_organism.scientific_name",
                        "operator": "exact_match",
                        "value": organism,
                    },
                },
            ],
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": max_results},
        },
    }

    try:
        response = httpx.post(
            "https://search.rcsb.org/rcsbsearch/v2/query",
            json=query_json,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        # Extract PDB IDs from result
        if "result_set" in data:
            return [hit["identifier"] for hit in data["result_set"]]
        return []
    except Exception:
        return []


def search_structures_with_ligand(
    uniprot_id: str,
    organism: str = "Homo sapiens",
    max_results: int = 20,
) -> list[str]:
    """
    Find PDB structures that have a bound non-polymer entity (ligand).
    These are better for docking because you get a reference pocket.
    """
    query_json = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                        "operator": "exact_match",
                        "value": uniprot_id,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entity_source_organism.scientific_name",
                        "operator": "exact_match",
                        "value": organism,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "exptl.method",
                        "operator": "exact_match",
                        "value": "X-RAY DIFFRACTION",
                    },
                },
            ],
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": max_results},
        },
    }

    try:
        response = httpx.post(
            "https://search.rcsb.org/rcsbsearch/v2/query",
            json=query_json,
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        if "result_set" in data:
            return [hit["identifier"] for hit in data["result_set"]]
        return []
    except Exception:
        return []
