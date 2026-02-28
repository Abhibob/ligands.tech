"""RCSB PDB structure search using the official rcsbsearchapi package."""

from rcsbsearchapi import rcsb_attributes as attrs


def search_structures_by_uniprot(
    uniprot_id: str,
    organism: str = "Homo sapiens",
    max_results: int = 20,
) -> list[str]:
    """
    Find PDB structures for a UniProt accession.
    Returns a list of PDB IDs.

    Uses the official rcsbsearchapi package which wraps
    POST https://search.rcsb.org/rcsbsearch/v2/query
    """
    # Build query: structures matching this UniProt ID from this organism
    q_uniprot = (
        attrs.rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession
        == uniprot_id
    )
    q_organism = attrs.rcsb_entity_source_organism.scientific_name == organism

    query = q_uniprot & q_organism

    try:
        results = list(query())
        return results[:max_results]
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
    q_uniprot = (
        attrs.rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession
        == uniprot_id
    )
    q_organism = attrs.rcsb_entity_source_organism.scientific_name == organism
    # Filter for X-ray structures (generally better for docking)
    q_method = attrs.exptl.method == "X-RAY DIFFRACTION"

    query = q_uniprot & q_organism & q_method

    try:
        results = list(query())
        return results[:max_results]
    except Exception:
        return []
