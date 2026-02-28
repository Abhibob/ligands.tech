#!/usr/bin/env python3
"""Quick verification script to test protein and ligand resolution.

Run this after installing to verify everything works:
    python verify_installation.py
"""

import asyncio
import sys
from pathlib import Path


def test_imports():
    """Test that all modules can be imported."""
    print("=" * 60)
    print("Testing imports...")
    print("=" * 60)

    try:
        from bind_tools.protein import resolve_protein, ProteinSearchInput

        print("✓ Protein module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import protein module: {e}")
        return False

    try:
        from bind_tools.ligand import resolve_ligand, LigandSearchInput

        print("✓ Ligand module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import ligand module: {e}")
        return False

    return True


async def test_protein_resolution():
    """Test protein resolution with a simple example."""
    print("\n" + "=" * 60)
    print("Testing protein resolution (CDK2)...")
    print("=" * 60)

    from bind_tools.protein import resolve_protein, ProteinSearchInput

    try:
        result = await resolve_protein(
            ProteinSearchInput(
                query="CDK2",
                max_structures=2,
                download_best=False,  # Skip download to save time
                workspace_dir="./verify_workspace",
            )
        )

        print(f"✓ Resolved protein: {result.gene_name}")
        print(f"  UniProt ID: {result.uniprot_id}")
        print(f"  Organism: {result.organism}")
        print(f"  Sequence length: {result.sequence_length} aa")
        print(f"  Structures found: {len(result.structures)}")
        print(f"  FASTA path: {result.fasta_path}")

        # Verify FASTA file exists
        if result.fasta_path and Path(result.fasta_path).exists():
            print(f"✓ FASTA file created successfully")
        else:
            print(f"✗ FASTA file not found at {result.fasta_path}")
            return False

        return True

    except Exception as e:
        print(f"✗ Protein resolution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_ligand_resolution():
    """Test ligand resolution with a simple example."""
    print("\n" + "=" * 60)
    print("Testing ligand resolution (aspirin)...")
    print("=" * 60)

    from bind_tools.ligand import resolve_ligand, LigandSearchInput

    try:
        result = await resolve_ligand(
            LigandSearchInput(
                query="aspirin",
                generate_3d=False,  # Skip 3D to save time
                workspace_dir="./verify_workspace",
            )
        )

        print(f"✓ Resolved ligand: {result.name}")
        print(f"  PubChem CID: {result.pubchem_cid}")
        print(f"  SMILES: {result.smiles}")

        if result.properties:
            print(f"  Molecular weight: {result.properties.molecular_weight:.2f} Da")
            print(f"  Formula: {result.properties.molecular_formula}")

        print(f"  2D SDF path: {result.sdf_2d_path}")

        # Verify SDF file exists
        if result.sdf_2d_path and Path(result.sdf_2d_path).exists():
            print(f"✓ SDF file created successfully")
        else:
            print(f"✗ SDF file not found at {result.sdf_2d_path}")
            return False

        return True

    except Exception as e:
        print(f"✗ Ligand resolution failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_cli_availability():
    """Test that CLI commands are available."""
    print("\n" + "=" * 60)
    print("Testing CLI availability...")
    print("=" * 60)

    import shutil

    bind_protein = shutil.which("bind-protein")
    bind_ligand = shutil.which("bind-ligand")

    if bind_protein:
        print(f"✓ bind-protein available at: {bind_protein}")
    else:
        print(f"✗ bind-protein command not found")
        print(f"  Try: pip install -e .")
        return False

    if bind_ligand:
        print(f"✓ bind-ligand available at: {bind_ligand}")
    else:
        print(f"✗ bind-ligand command not found")
        print(f"  Try: pip install -e .")
        return False

    return True


async def main():
    """Run all verification tests."""
    print("\n🔍 BindingOps Installation Verification")
    print("=" * 60)

    results = []

    # Test 1: Imports
    results.append(("Imports", test_imports()))

    # Test 2: CLI availability
    results.append(("CLI commands", test_cli_availability()))

    # Test 3: Protein resolution
    results.append(("Protein resolution", await test_protein_resolution()))

    # Test 4: Ligand resolution
    results.append(("Ligand resolution", await test_ligand_resolution()))

    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 ALL TESTS PASSED!")
        print("\nYou can now use:")
        print("  - bind-protein resolve --name EGFR --json-out result.json")
        print("  - bind-ligand resolve --name erlotinib --json-out result.json")
        print("\nOr import in Python:")
        print("  from bind_tools.protein import resolve_protein")
        print("  from bind_tools.ligand import resolve_ligand")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        print("\nTroubleshooting:")
        print("  1. Make sure you installed: pip install -e .")
        print("  2. Check internet connection (tests hit real APIs)")
        print("  3. See README.md for more details")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
