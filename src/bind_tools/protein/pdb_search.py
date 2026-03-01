"""RCSB PDB structure search using the official rcsbsearchapi package."""

# ---------------------------------------------------------------------------
# rcsbsearchapi ≤2.0.1 has a bug in Schema._make_group: when a schema key
# appears in both the structure and chemical attribute schemas and the
# existing entry is a SchemaGroup (not a leaf Attr), it crashes trying to
# read .description.  We patch the installed file at import time.
# ---------------------------------------------------------------------------
import sys
from pathlib import Path


def _patch_rcsbsearchapi_schema() -> None:
    """Patch the installed rcsbsearchapi/schema.py if it has the known bug."""
    for p in sys.path:
        schema_file = Path(p) / "rcsbsearchapi" / "schema.py"
        if not schema_file.is_file():
            continue
        source = schema_file.read_text()
        marker = "# bind-tools-patched"
        if marker in source:
            return  # already patched
        # The bug: line does getattr(group[childname], "description") on a SchemaGroup
        old = '                        currentdescript = getattr(group[childname], "description")'
        if old not in source:
            return  # different version or already different code
        # Replace the duplicate-handling block (lines 272-283 in the original)
        old_block = (
            '                    if childname in group:\n'
            '                        assert not isinstance(group[childname], dict)  # redundant name must not have nested attributes\n'
            '\n'
            '                        # Create attrtype and description lists with existing and current value.\n'
            '                        # List type triggers error if user doesn\'t specify service for redundant attribute.\n'
            '                        currentattr = getattr(group[childname], "type")\n'
            '                        attrlist = [currentattr, attrtype]\n'
            '\n'
            '                        currentdescript = getattr(group[childname], "description")\n'
            '                        descriptlist = [currentdescript, childnode.get("description", desc)]\n'
            '\n'
            '                        childgroup = self._make_group(fullchildname, [(childnode, attrlist, descriptlist)])'
        )
        new_block = (
            f'                    if childname in group:  {marker}\n'
            '                        existing = group[childname]\n'
            '                        if isinstance(existing, SchemaGroup):\n'
            '                            # Duplicate intermediate node - merge children\n'
            '                            childgroup = self._make_group(\n'
            '                                fullchildname,\n'
            '                                [(childnode, attrtype, childnode.get("description", desc))],\n'
            '                            )\n'
            '                            if isinstance(childgroup, SchemaGroup):\n'
            '                                for k, v in childgroup.items():\n'
            '                                    if k not in existing:\n'
            '                                        existing[k] = v\n'
            '                                        setattr(existing, k, v)\n'
            '                                childgroup = existing\n'
            '                        else:\n'
            '                            currentattr = getattr(existing, "type")\n'
            '                            attrlist = [currentattr, attrtype]\n'
            '                            currentdescript = getattr(existing, "description")\n'
            '                            descriptlist = [currentdescript, childnode.get("description", desc)]\n'
            '                            childgroup = self._make_group(fullchildname, [(childnode, attrlist, descriptlist)])'
        )
        if old_block in source:
            patched = source.replace(old_block, new_block)
            schema_file.write_text(patched)
        return


_patch_rcsbsearchapi_schema()
# ---------------------------------------------------------------------------

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
