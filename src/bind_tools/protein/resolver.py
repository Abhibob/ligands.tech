"""Main protein resolution pipeline orchestrator."""

from pathlib import Path

from . import pdb_data, pdb_search, uniprot
from .models import ProteinSearchInput, ResolvedProtein, StructureHit


async def resolve_protein(inp: ProteinSearchInput) -> ResolvedProtein:
    """
    Full resolution pipeline: name → UniProt → PDB → files.

    This is the main function the orchestrator / agents call.
    """
    workspace = Path(inp.workspace_dir or "./workspace")

    # 1. Resolve via UniProt
    uni = await uniprot.search_uniprot(inp.query, inp.organism)
    if not uni:
        raise ValueError(
            f"Could not find protein '{inp.query}' "
            f"(organism: {inp.organism}) in UniProt"
        )

    accession = uni["accession"]

    # 2. Write FASTA to workspace
    fasta_text = await uniprot.fetch_fasta(accession)
    fasta_dir = workspace / "proteins"
    fasta_dir.mkdir(parents=True, exist_ok=True)
    fasta_path = fasta_dir / f"{accession}.fasta"
    fasta_path.write_text(fasta_text, encoding="utf-8")

    # 3. Search for PDB structures
    pdb_ids = pdb_search.search_structures_by_uniprot(
        accession,
        organism=inp.organism,
        max_results=inp.max_structures * 4,  # fetch extra, we'll rank and trim
    )

    # 4. Fetch details for each structure
    structures: list[StructureHit] = []
    for pdb_id in pdb_ids:
        try:
            hit = await pdb_data.fetch_structure_details(pdb_id)
            structures.append(hit)
        except Exception:
            continue  # skip structures we can't fetch

    # 5. Rank by suitability for docking
    structures = pdb_data.rank_structures(structures)
    structures = structures[: inp.max_structures]

    # 6. Fetch binding sites for top structures
    all_binding_sites = []
    for hit in structures[:3]:  # binding sites for top 3 only
        try:
            sites = await pdb_data.fetch_binding_sites(hit.pdb_id)
            hit.binding_sites = sites
            all_binding_sites.extend(sites)
        except Exception:
            continue

    # 7. Download best structure
    best = structures[0] if structures else None
    if best and inp.download_best:
        struct_dir = workspace / "proteins" / "structures"
        try:
            pdb_path = await pdb_data.download_structure(best.pdb_id, struct_dir, format="pdb")
            best.pdb_path = pdb_path

            cif_path = await pdb_data.download_structure(best.pdb_id, struct_dir, format="cif")
            best.cif_path = cif_path
        except Exception:
            pass  # structure still usable without local file

    # 8. Build the result
    gene = uni["gene_name"] or accession

    return ResolvedProtein(
        query=inp.query,
        uniprot_id=accession,
        gene_name=gene,
        protein_name=uni["protein_name"],
        organism=uni["organism"],
        sequence=uni["sequence"],
        sequence_length=uni["length"],
        fasta_path=str(fasta_path),
        structures=structures,
        best_structure=best,
        binding_sites=all_binding_sites,
        custom_id=f"protein-{gene.lower()}",
    )
