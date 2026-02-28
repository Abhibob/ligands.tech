"""RDKit-based 3D conformer generation from SMILES.

This is an optional module. If RDKit is not installed, 3D generation will fall back to PubChem.
"""

from pathlib import Path

# Try to import RDKit (optional dependency)
try:
    from rdkit import Chem
    from rdkit.Chem import AllChem

    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False


def is_available() -> bool:
    """Check if RDKit is available."""
    return RDKIT_AVAILABLE


def generate_3d_from_smiles(smiles: str, output_path: str | Path) -> str:
    """
    Generate 3D coordinates from SMILES string using RDKit.

    Args:
        smiles: SMILES string
        output_path: Path to output SDF file

    Returns:
        Path to generated SDF file

    Raises:
        ImportError: If RDKit is not installed
        ValueError: If SMILES is invalid or 3D generation fails
    """
    if not RDKIT_AVAILABLE:
        raise ImportError(
            "RDKit is not installed. Install with: pip install rdkit\n"
            "Falling back to PubChem 3D conformers."
        )

    # Parse SMILES
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")

    # Add hydrogens
    mol = Chem.AddHs(mol)

    # Generate 3D conformer using ETKDG method (Extended Electron Cloud)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42  # Reproducibility

    result = AllChem.EmbedMolecule(mol, params)
    if result != 0:
        raise ValueError(f"Failed to generate 3D conformer for SMILES: {smiles}")

    # Optimize geometry with MMFF force field
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        # MMFF might fail for some molecules, try UFF
        try:
            AllChem.UFFOptimizeMolecule(mol, maxIters=200)
        except Exception:
            # Optimization failed, but we still have coordinates
            pass

    # Write to SDF file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = Chem.SDWriter(str(output_path))
    writer.write(mol)
    writer.close()

    return str(output_path)


def generate_multiple_conformers(
    smiles: str, output_path: str | Path, num_conformers: int = 10
) -> str:
    """
    Generate multiple 3D conformers from SMILES.

    Args:
        smiles: SMILES string
        output_path: Path to output SDF file (will contain multiple conformers)
        num_conformers: Number of conformers to generate

    Returns:
        Path to SDF file with all conformers
    """
    if not RDKIT_AVAILABLE:
        raise ImportError("RDKit is not installed. Install with: pip install rdkit")

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES string: {smiles}")

    mol = Chem.AddHs(mol)

    # Generate multiple conformers
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    params.numThreads = 0  # Use all available cores

    cids = AllChem.EmbedMultipleConfs(mol, numConfs=num_conformers, params=params)

    if len(cids) == 0:
        raise ValueError(f"Failed to generate conformers for SMILES: {smiles}")

    # Optimize each conformer
    for cid in cids:
        try:
            AllChem.MMFFOptimizeMolecule(mol, confId=cid, maxIters=200)
        except Exception:
            try:
                AllChem.UFFOptimizeMolecule(mol, confId=cid, maxIters=200)
            except Exception:
                pass

    # Write all conformers to single SDF file
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    writer = Chem.SDWriter(str(output_path))
    for cid in cids:
        writer.write(mol, confId=cid)
    writer.close()

    return str(output_path)
