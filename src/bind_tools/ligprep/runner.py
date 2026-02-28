"""Ligand preparation pipeline: protonate, charge, conformers, format conversion."""

from __future__ import annotations

import csv
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from bind_tools.common.errors import ValidationError
from bind_tools.common.runner import ensure_dir, ensure_file

from .models import LigPrepInput, LigPrepItemResult, LigPrepSpec, LigPrepSummary

# ── Optional imports ─────────────────────────────────────────────────────────

_RDKIT = False
try:
    from rdkit import Chem  # type: ignore[import-untyped]
    from rdkit.Chem import AllChem, Descriptors  # type: ignore[import-untyped]

    _RDKIT = True
except ImportError:
    Chem = None  # type: ignore[assignment]
    AllChem = None  # type: ignore[assignment]
    Descriptors = None  # type: ignore[assignment]

_OBABEL = False
try:
    _obabel_check = subprocess.run(
        ["obabel", "-V"], capture_output=True, text=True, timeout=5
    )
    if _obabel_check.returncode == 0:
        _OBABEL = True
        _OBABEL_VERSION = _obabel_check.stdout.strip().split("\n")[0]
    else:
        _OBABEL_VERSION = ""
except Exception:
    _OBABEL_VERSION = ""

_MEEKO = False
_MEEKO_VERSION = ""
try:
    from meeko import MoleculePreparation  # type: ignore[import-untyped]

    _MEEKO = True
    try:
        import meeko  # type: ignore[import-untyped]
        _MEEKO_VERSION = getattr(meeko, "__version__", "unknown")
    except Exception:
        _MEEKO_VERSION = "unknown"
except ImportError:
    MoleculePreparation = None  # type: ignore[assignment,misc]


# ── Availability checks ─────────────────────────────────────────────────────


def check_rdkit_installed() -> bool:
    return _RDKIT


def check_obabel_installed() -> bool:
    return _OBABEL


def check_meeko_installed() -> bool:
    return _MEEKO


# ── Engine selection ─────────────────────────────────────────────────────────


def _select_engine(requested: str) -> str:
    """Select the best available engine. auto picks rdkit > obabel > error."""
    if requested == "rdkit":
        if not _RDKIT:
            raise ValidationError("RDKit requested but not installed (pip install rdkit)")
        return "rdkit"
    if requested == "obabel":
        if not _OBABEL:
            raise ValidationError("Open Babel requested but not installed")
        return "obabel"
    if requested == "meeko":
        if not _MEEKO:
            raise ValidationError("Meeko requested but not installed (pip install meeko)")
        return "meeko"

    # auto
    if _RDKIT:
        return "rdkit"
    if _OBABEL:
        return "obabel"
    raise ValidationError(
        "No ligand preparation engine available. "
        "Install RDKit (pip install rdkit) or Open Babel."
    )


def _engine_version(engine: str) -> str:
    if engine == "rdkit" and _RDKIT:
        try:
            from rdkit import rdBase  # type: ignore[import-untyped]
            return rdBase.rdkitVersion
        except Exception:
            return "unknown"
    if engine == "obabel":
        return _OBABEL_VERSION
    if engine == "meeko":
        return _MEEKO_VERSION
    return ""


# ── Input resolution ─────────────────────────────────────────────────────────


def _resolve_input(
    inp: LigPrepInput, work_dir: Path
) -> tuple[Any, str, str]:
    """Resolve a LigPrepInput to (RDKit Mol | None, canonical_smiles, label).

    Returns (mol, smiles, label). mol may be None if RDKit not available.
    """
    if not _RDKIT:
        raise ValidationError("RDKit is required for ligand preparation (pip install rdkit)")

    label = inp.id or ""

    if inp.sdf_path:
        sdf_file = ensure_file(inp.sdf_path, label="input SDF")
        supplier = Chem.SDMolSupplier(str(sdf_file), removeHs=False)
        mol = next(iter(supplier), None)
        if mol is None:
            raise ValidationError(f"Failed to read molecule from {sdf_file}")
        smiles = Chem.MolToSmiles(Chem.RemoveHs(mol))
        label = label or sdf_file.stem
        return mol, smiles, label

    if inp.mol2_path:
        mol2_file = ensure_file(inp.mol2_path, label="input MOL2")
        mol = Chem.MolFromMol2File(str(mol2_file), removeHs=False)
        if mol is None:
            raise ValidationError(f"Failed to read molecule from {mol2_file}")
        smiles = Chem.MolToSmiles(Chem.RemoveHs(mol))
        label = label or mol2_file.stem
        return mol, smiles, label

    if inp.smiles:
        mol = Chem.MolFromSmiles(inp.smiles)
        if mol is None:
            raise ValidationError(f"Invalid SMILES: {inp.smiles}")
        smiles = Chem.MolToSmiles(mol)
        label = label or smiles[:30]
        return mol, smiles, label

    if inp.name or inp.pubchem_cid is not None:
        # Use ligand resolver to get SMILES/SDF
        import asyncio
        from bind_tools.ligand.resolver import resolve_ligand
        from bind_tools.ligand.models import LigandSearchInput

        query = inp.name or f"CID:{inp.pubchem_cid}"
        resolved = asyncio.run(resolve_ligand(LigandSearchInput(
            query=query,
            generate_3d=False,
            workspace_dir=str(work_dir),
        )))

        if resolved.smiles:
            mol = Chem.MolFromSmiles(resolved.smiles)
            if mol is None:
                raise ValidationError(f"Failed to parse resolved SMILES for {query}")
            smiles = Chem.MolToSmiles(mol)
            label = label or resolved.name or query
            return mol, smiles, label

        raise ValidationError(f"Could not resolve ligand: {query}")

    raise ValidationError("LigPrepInput must have one of: sdfPath, mol2Path, smiles, name, pubchemCid")


# ── Preparation steps ────────────────────────────────────────────────────────


def _add_hydrogens(mol: Any, ph: float) -> Any:
    """Add hydrogens. RDKit AddHs doesn't do pH-aware addition natively."""
    return Chem.AddHs(mol)


def _assign_charges(mol: Any, model: str) -> Any:
    """Assign partial charges using Gasteiger or MMFF94."""
    if model == "gasteiger":
        AllChem.ComputeGasteigerCharges(mol)
    elif model == "mmff94":
        # MMFF partial charges are computed during MMFF property calculation
        mp = AllChem.MMFFGetMoleculeProperties(mol)
        if mp is not None:
            for i in range(mol.GetNumAtoms()):
                charge = mp.GetMMFFPartialCharge(i)
                mol.GetAtomWithIdx(i).SetDoubleProp("_MMFFPartialCharge", charge)
    # model == "none" — skip
    return mol


def _generate_conformers(mol: Any, n: int) -> Any:
    """Generate 3D conformers using ETKDGv3 + MMFF optimization."""
    params = AllChem.ETKDGv3()
    params.randomSeed = 42

    if n == 1:
        result = AllChem.EmbedMolecule(mol, params)
        if result != 0:
            # Fallback: try with random coords
            params.useRandomCoords = True
            AllChem.EmbedMolecule(mol, params)
    else:
        AllChem.EmbedMultipleConfs(mol, numConfs=n, params=params)

    # Optimize each conformer
    for conf_id in range(mol.GetNumConformers()):
        try:
            AllChem.MMFFOptimizeMolecule(mol, confId=conf_id, maxIters=200)
        except Exception:
            try:
                AllChem.UFFOptimizeMolecule(mol, confId=conf_id, maxIters=200)
            except Exception:
                pass

    return mol


# ── Output writers ───────────────────────────────────────────────────────────


def _write_sdf(mol: Any, path: Path) -> str:
    """Write molecule to SDF file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = Chem.SDWriter(str(path))
    for conf_id in range(mol.GetNumConformers()):
        writer.write(mol, confId=conf_id)
    writer.close()
    return str(path)


def _write_pdbqt(mol: Any, sdf_path: Path, pdbqt_path: Path) -> tuple[str | None, list[str]]:
    """Write PDBQT using meeko (preferred) or obabel. Returns (path, warnings)."""
    warnings: list[str] = []
    pdbqt_path.parent.mkdir(parents=True, exist_ok=True)

    if _MEEKO:
        try:
            preparator = MoleculePreparation()
            mol_setups = preparator.prepare(mol)
            for setup in mol_setups:
                pdbqt_string, is_ok, err_msg = setup.write_pdbqt_string()
                if is_ok:
                    pdbqt_path.write_text(pdbqt_string)
                    return str(pdbqt_path), warnings
                else:
                    warnings.append(f"Meeko PDBQT error: {err_msg}")
        except Exception as exc:
            warnings.append(f"Meeko failed: {exc}")

    if _OBABEL:
        try:
            result = subprocess.run(
                ["obabel", str(sdf_path), "-opdbqt", "-O", str(pdbqt_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and pdbqt_path.exists():
                return str(pdbqt_path), warnings
            else:
                warnings.append(f"obabel PDBQT conversion failed: {result.stderr}")
        except Exception as exc:
            warnings.append(f"obabel failed: {exc}")

    warnings.append("PDBQT output skipped: neither meeko nor obabel available")
    return None, warnings


def _write_mol2(sdf_path: Path, mol2_path: Path) -> tuple[str | None, list[str]]:
    """Write MOL2 via obabel. Returns (path, warnings)."""
    warnings: list[str] = []
    mol2_path.parent.mkdir(parents=True, exist_ok=True)

    if _OBABEL:
        try:
            result = subprocess.run(
                ["obabel", str(sdf_path), "-omol2", "-O", str(mol2_path)],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0 and mol2_path.exists():
                return str(mol2_path), warnings
            else:
                warnings.append(f"obabel MOL2 conversion failed: {result.stderr}")
        except Exception as exc:
            warnings.append(f"obabel failed: {exc}")
    else:
        warnings.append("MOL2 output skipped: obabel not available")

    return None, warnings


# ── Property computation ─────────────────────────────────────────────────────


def _compute_properties(mol: Any) -> dict[str, Any]:
    """Compute molecular properties using RDKit Descriptors."""
    mol_no_h = Chem.RemoveHs(mol)
    return {
        "molecularWeight": round(Descriptors.ExactMolWt(mol_no_h), 3),
        "logp": round(Descriptors.MolLogP(mol_no_h), 3),
        "rotatableBonds": Descriptors.NumRotatableBonds(mol_no_h),
        "netCharge": Chem.GetFormalCharge(mol_no_h),
    }


# ── Manifest loader ─────────────────────────────────────────────────────────


def _load_manifest(path: Path) -> list[LigPrepInput]:
    """Parse a CSV or JSONL manifest file into LigPrepInput items."""
    items: list[LigPrepInput] = []
    suffix = path.suffix.lower()

    if suffix == ".csv":
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                inp = LigPrepInput(
                    smiles=row.get("smiles") or None,
                    name=row.get("name") or None,
                    id=row.get("id", ""),
                    sdfPath=row.get("sdf_path") or None,
                )
                items.append(inp)
    elif suffix in (".jsonl", ".ndjson"):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                items.append(LigPrepInput.model_validate(data))
    else:
        raise ValidationError(f"Unsupported manifest format: {suffix} (expected .csv or .jsonl)")

    return items


# ── Single-item preparation ──────────────────────────────────────────────────


def prepare_single(
    inp: LigPrepInput,
    opts: Any,
    work_dir: Path,
) -> LigPrepItemResult:
    """Prepare a single ligand: resolve → addH → charges → conformers → write."""
    start = time.monotonic()
    warnings: list[str] = []
    errors: list[str] = []

    query = inp.smiles or inp.name or (f"CID:{inp.pubchem_cid}" if inp.pubchem_cid else "") or inp.sdf_path or inp.mol2_path or ""

    try:
        mol, canonical_smiles, label = _resolve_input(inp, work_dir)

        # Add hydrogens
        mol = _add_hydrogens(mol, opts.ph)

        # Assign charges
        if opts.charge_model != "none":
            mol = _assign_charges(mol, opts.charge_model)

        # Generate conformers
        mol = _generate_conformers(mol, opts.num_conformers)

        if mol.GetNumConformers() == 0:
            errors.append("Failed to generate any conformers")
            return LigPrepItemResult(
                id=inp.id or label,
                inputQuery=str(query),
                status="failed",
                canonicalSmiles=canonical_smiles,
                errors=errors,
                warnings=warnings,
                runtimeSeconds=round(time.monotonic() - start, 3),
            )

        # Compute properties
        props = _compute_properties(mol)

        # Write outputs
        safe_label = label.replace("/", "_").replace(" ", "_")[:50]
        sdf_out = None
        pdbqt_out = None
        mol2_out = None

        if "sdf" in opts.output_formats:
            sdf_path = work_dir / f"{safe_label}.sdf"
            sdf_out = _write_sdf(mol, sdf_path)

        if "pdbqt" in opts.output_formats:
            sdf_for_conv = work_dir / f"{safe_label}.sdf"
            if not sdf_for_conv.exists():
                _write_sdf(mol, sdf_for_conv)
            pdbqt_path = work_dir / f"{safe_label}.pdbqt"
            pdbqt_out, pdbqt_warns = _write_pdbqt(mol, sdf_for_conv, pdbqt_path)
            warnings.extend(pdbqt_warns)

        if "mol2" in opts.output_formats:
            sdf_for_conv = work_dir / f"{safe_label}.sdf"
            if not sdf_for_conv.exists():
                _write_sdf(mol, sdf_for_conv)
            mol2_path = work_dir / f"{safe_label}.mol2"
            mol2_out, mol2_warns = _write_mol2(sdf_for_conv, mol2_path)
            warnings.extend(mol2_warns)

        return LigPrepItemResult(
            id=inp.id or label,
            inputQuery=str(query),
            status="succeeded",
            canonicalSmiles=canonical_smiles,
            netCharge=props.get("netCharge"),
            rotatableBonds=props.get("rotatableBonds"),
            molecularWeight=props.get("molecularWeight"),
            logp=props.get("logp"),
            sdfPath=sdf_out,
            pdbqtPath=pdbqt_out,
            mol2Path=mol2_out,
            numConformers=mol.GetNumConformers(),
            warnings=warnings,
            runtimeSeconds=round(time.monotonic() - start, 3),
        )

    except Exception as exc:
        errors.append(str(exc))
        return LigPrepItemResult(
            id=inp.id or str(query),
            inputQuery=str(query),
            status="failed",
            errors=errors,
            warnings=warnings,
            runtimeSeconds=round(time.monotonic() - start, 3),
        )


# ── Main pipeline ────────────────────────────────────────────────────────────


def run_prepare(spec: LigPrepSpec, artifacts_dir: Path) -> dict[str, Any]:
    """Run the full ligand preparation pipeline.

    Returns a dict matching the LigPrepSummary schema.
    """
    engine = _select_engine(spec.options.engine.value)
    engine_ver = _engine_version(engine)

    artifacts_dir = ensure_dir(artifacts_dir, label="artifacts directory", create=True)

    # Collect all ligands
    all_ligands: list[LigPrepInput] = list(spec.ligands)

    if spec.manifest_path:
        manifest_file = ensure_file(spec.manifest_path, label="manifest")
        all_ligands.extend(_load_manifest(manifest_file))

    if not all_ligands:
        raise ValidationError("No ligands provided (use --ligand or --manifest)")

    # Process each ligand sequentially
    items: list[LigPrepItemResult] = []
    for i, lig_inp in enumerate(all_ligands):
        if not lig_inp.id:
            lig_inp.id = f"lig_{i}"
        work_dir = artifacts_dir / lig_inp.id
        work_dir.mkdir(parents=True, exist_ok=True)
        result = prepare_single(lig_inp, spec.options, work_dir)
        items.append(result)

    succeeded = sum(1 for it in items if it.status == "succeeded")
    failed = sum(1 for it in items if it.status == "failed")
    skipped = sum(1 for it in items if it.status == "skipped")

    provenance: dict[str, str] = {"engine": engine}
    if "pdbqt" in spec.options.output_formats:
        if _MEEKO:
            provenance["pdbqt"] = "meeko"
        elif _OBABEL:
            provenance["pdbqt"] = "obabel"
    if "mol2" in spec.options.output_formats:
        if _OBABEL:
            provenance["mol2"] = "obabel"

    summary = LigPrepSummary(
        total=len(items),
        succeeded=succeeded,
        failed=failed,
        skipped=skipped,
        items=items,
        engineUsed=engine,
        engineVersion=engine_ver,
        conversionProvenance=provenance,
    )

    return summary.model_dump(by_alias=True, mode="json")
