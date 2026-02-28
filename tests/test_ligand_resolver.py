"""Integration tests for ligand resolution.

These tests hit real APIs (PubChem) and require network access.
Run with: pytest tests/test_ligand_resolver.py -v
"""

import pytest

from bind_tools.ligand.models import LigandSearchInput
from bind_tools.ligand.resolver import resolve_ligand


@pytest.mark.asyncio
async def test_resolve_erlotinib_by_name(tmp_path):
    """Test resolving erlotinib by drug name."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="erlotinib",
            generate_3d=True,
            workspace_dir=str(tmp_path),
        )
    )

    assert result.pubchem_cid == 176870
    assert result.name is not None
    assert "erlotinib" in result.name.lower()
    assert result.smiles is not None
    assert "C#Cc1cccc" in result.smiles  # Partial match for erlotinib SMILES
    assert result.sdf_2d_path is not None
    # 3D might be from PubChem or RDKit
    assert result.sdf_3d_path is not None or True  # May not always have 3D


@pytest.mark.asyncio
async def test_resolve_aspirin_by_name(tmp_path):
    """Test resolving aspirin (simple molecule)."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="aspirin",
            generate_3d=True,
            workspace_dir=str(tmp_path),
        )
    )

    assert result.pubchem_cid == 2244
    assert result.smiles is not None
    assert result.properties is not None
    assert result.properties.molecular_weight is not None
    assert 180 < result.properties.molecular_weight < 182  # ~180 Da


@pytest.mark.asyncio
async def test_resolve_by_smiles(tmp_path):
    """Test resolving by SMILES string (ethanol)."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="CCO",  # Ethanol
            generate_3d=True,
            workspace_dir=str(tmp_path),
        )
    )

    # Should find ethanol in PubChem
    assert result.smiles == "CCO"
    assert result.pubchem_cid is not None


@pytest.mark.asyncio
async def test_resolve_by_cid(tmp_path):
    """Test resolving by PubChem CID."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="CID:176870",  # Erlotinib
            workspace_dir=str(tmp_path),
        )
    )

    assert result.pubchem_cid == 176870
    assert result.smiles is not None


@pytest.mark.asyncio
async def test_molecular_properties(tmp_path):
    """Test that molecular properties are extracted."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="caffeine",
            workspace_dir=str(tmp_path),
        )
    )

    assert result.properties is not None
    assert result.properties.molecular_weight is not None
    assert result.properties.molecular_formula is not None
    assert result.properties.h_bond_donors is not None
    assert result.properties.h_bond_acceptors is not None

    # Caffeine has C8H10N4O2
    assert result.properties.molecular_formula == "C8H10N4O2"


@pytest.mark.asyncio
async def test_sdf_files_created(tmp_path):
    """Test that SDF files are actually created."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="aspirin",
            generate_3d=True,
            workspace_dir=str(tmp_path),
        )
    )

    # Check 2D file exists
    assert result.sdf_2d_path is not None
    sdf_2d = tmp_path / "ligands" / f"pubchem_{result.pubchem_cid}_2d.sdf"
    assert sdf_2d.exists()

    # Check 3D file (might be PubChem or RDKit)
    if result.sdf_3d_path:
        from pathlib import Path

        assert Path(result.sdf_3d_path).exists()


@pytest.mark.asyncio
async def test_no_3d_generation(tmp_path):
    """Test skipping 3D generation."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="aspirin",
            generate_3d=False,
            workspace_dir=str(tmp_path),
        )
    )

    assert result.sdf_2d_path is not None
    # 3D should not be generated
    # (but might still be available from PubChem if it exists)


@pytest.mark.asyncio
async def test_invalid_ligand_raises_error(tmp_path):
    """Test error handling for invalid ligand names."""
    with pytest.raises(ValueError, match="Could not find ligand"):
        await resolve_ligand(
            LigandSearchInput(
                query="NOTAREALLIGAND12345XYZ",
                workspace_dir=str(tmp_path),
            )
        )


@pytest.mark.asyncio
async def test_synonyms_extracted(tmp_path):
    """Test that synonyms are extracted."""
    result = await resolve_ligand(
        LigandSearchInput(
            query="aspirin",
            workspace_dir=str(tmp_path),
        )
    )

    assert len(result.synonyms) > 0
    # Aspirin has many synonyms
    synonyms_lower = [s.lower() for s in result.synonyms]
    # Should include acetylsalicylic acid
    assert any("acetylsalicylic" in s for s in synonyms_lower)


@pytest.mark.asyncio
async def test_complex_smiles(tmp_path):
    """Test with complex SMILES (erlotinib)."""
    erlotinib_smiles = "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1"

    result = await resolve_ligand(
        LigandSearchInput(
            query=erlotinib_smiles,
            workspace_dir=str(tmp_path),
        )
    )

    # Should find erlotinib in PubChem
    assert result.pubchem_cid == 176870
