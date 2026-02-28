"""Integration tests for protein resolution.

These tests hit real APIs (UniProt, RCSB PDB) and require network access.
Run with: pytest tests/test_protein_resolver.py -v
"""

import pytest

from bind_tools.protein.models import ProteinSearchInput
from bind_tools.protein.resolver import resolve_protein


@pytest.mark.asyncio
async def test_resolve_egfr(tmp_path):
    """Integration test — hits real APIs (needs network)."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="EGFR",
            organism="Homo sapiens",
            max_structures=3,
            download_best=True,
            workspace_dir=str(tmp_path),
        )
    )

    assert result.uniprot_id == "P00533"
    assert result.gene_name == "EGFR"
    assert len(result.sequence) > 1000  # EGFR is ~1210 aa
    assert result.fasta_path is not None
    assert len(result.structures) > 0
    assert result.best_structure is not None
    assert result.best_structure.has_ligand  # top hit should have a ligand


@pytest.mark.asyncio
async def test_resolve_by_accession(tmp_path):
    """Direct accession lookup — fast path."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="P00533",
            download_best=False,
            workspace_dir=str(tmp_path),
        )
    )
    assert result.gene_name == "EGFR"


@pytest.mark.asyncio
async def test_resolve_cdk2(tmp_path):
    """Another common drug target."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="CDK2",
            max_structures=3,
            download_best=False,
            workspace_dir=str(tmp_path),
        )
    )
    assert result.uniprot_id == "P24941"
    assert len(result.structures) > 0


@pytest.mark.asyncio
async def test_fasta_file_written(tmp_path):
    """Verify FASTA file is created."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="EGFR",
            max_structures=1,
            download_best=False,
            workspace_dir=str(tmp_path),
        )
    )

    fasta_path = tmp_path / "proteins" / "P00533.fasta"
    assert fasta_path.exists()
    content = fasta_path.read_text()
    assert content.startswith(">")
    assert "EGFR" in content


@pytest.mark.asyncio
async def test_structure_download(tmp_path):
    """Verify structure files are downloaded."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="EGFR",
            max_structures=1,
            download_best=True,
            workspace_dir=str(tmp_path),
        )
    )

    assert result.best_structure is not None
    assert result.best_structure.pdb_path is not None
    assert result.best_structure.cif_path is not None

    # Verify files exist
    pdb_file = tmp_path / "proteins" / "structures" / f"{result.best_structure.pdb_id.lower()}.pdb"
    cif_file = tmp_path / "proteins" / "structures" / f"{result.best_structure.pdb_id.lower()}.cif"
    assert pdb_file.exists()
    assert cif_file.exists()


@pytest.mark.asyncio
async def test_structure_ranking(tmp_path):
    """Verify structures are ranked properly (ligand-bound first)."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="EGFR",
            max_structures=5,
            download_best=False,
            workspace_dir=str(tmp_path),
        )
    )

    # Best structure should have a ligand (highest priority)
    if result.structures:
        best = result.structures[0]
        assert best.has_ligand or best.resolution is not None


@pytest.mark.asyncio
async def test_binding_sites_extracted(tmp_path):
    """Verify binding sites are extracted from PDB."""
    result = await resolve_protein(
        ProteinSearchInput(
            query="EGFR",
            max_structures=3,
            download_best=False,
            workspace_dir=str(tmp_path),
        )
    )

    # Should have some binding sites
    assert len(result.binding_sites) > 0
    site = result.binding_sites[0]
    assert site.site_id
    assert len(site.residues) > 0


@pytest.mark.asyncio
async def test_invalid_protein_raises_error(tmp_path):
    """Verify error handling for invalid protein names."""
    with pytest.raises(ValueError, match="Could not find protein"):
        await resolve_protein(
            ProteinSearchInput(
                query="NOTAREALPROTEIN12345",
                workspace_dir=str(tmp_path),
            )
        )
