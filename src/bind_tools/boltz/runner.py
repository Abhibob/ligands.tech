"""Boltz runner: translate request to upstream YAML, invoke boltz predict, parse outputs."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from bind_tools.common.errors import InputMissingError, UpstreamError, ValidationError
from bind_tools.common.runner import detect_device, ensure_dir, ensure_file, run_subprocess

from .models import BoltzPredictSpec


# ── Translate house format -> upstream Boltz YAML ───────────────────────────


def translate_to_upstream_yaml(spec: BoltzPredictSpec) -> dict[str, Any]:
    """Convert our BoltzPredictSpec into the dict that Boltz CLI expects as its input YAML."""

    sequences: list[dict[str, Any]] = []

    # --- protein target ---
    target = spec.target
    protein_seq: str | None = None

    if target.protein_fasta_path:
        fasta_path = ensure_file(target.protein_fasta_path, "protein FASTA")
        protein_seq = _read_fasta_sequence(fasta_path)
    elif target.protein_sequence:
        protein_seq = target.protein_sequence
    elif target.protein_pdb_path:
        # Boltz can accept structure files directly; pass as template later.
        # We still need a sequence – caller should provide one; raise if missing.
        raise ValidationError(
            "proteinPdbPath supplied without proteinSequence or proteinFastaPath. "
            "Please also provide the sequence for the target protein."
        )
    elif target.protein_cif_path:
        raise ValidationError(
            "proteinCifPath supplied without proteinSequence or proteinFastaPath. "
            "Please also provide the sequence for the target protein."
        )

    if protein_seq:
        protein_entry: dict[str, Any] = {"protein": {"id": target.name or "A", "sequence": protein_seq}}
        sequences.append(protein_entry)

    # --- ligands ---
    for lig in spec.ligands:
        if lig.smiles:
            sequences.append({"ligand": {"id": lig.id or "L", "smiles": lig.smiles}})
        elif lig.sdf_path:
            ensure_file(lig.sdf_path, "ligand SDF")
            # Boltz accepts CCD codes or SMILES; for SDF we read and convert later.
            # For now, represent as smiles placeholder – the upstream CLI may not
            # support SDF directly. We note this as a limitation.
            sequences.append({"ligand": {"id": lig.id or "L", "sdf": lig.sdf_path}})
        elif lig.mol2_path:
            ensure_file(lig.mol2_path, "ligand MOL2")
            sequences.append({"ligand": {"id": lig.id or "L", "mol2": lig.mol2_path}})

    upstream: dict[str, Any] = {
        "version": 2,
        "sequences": sequences,
    }

    # --- constraints ---
    constraints = spec.constraints
    if constraints.pocket_residues or constraints.contacts or constraints.method_conditioning:
        cons_section: dict[str, Any] = {}
        if constraints.pocket_residues:
            cons_section["pocket_residues"] = constraints.pocket_residues
        if constraints.contacts:
            cons_section["contacts"] = constraints.contacts
        if constraints.method_conditioning:
            cons_section["method_conditioning"] = constraints.method_conditioning
        upstream["constraints"] = cons_section

    # --- properties / affinity ---
    if spec.task in ("affinity", "both"):
        upstream.setdefault("properties", {})["affinity"] = True

    return upstream


# ── Run boltz predict ───────────────────────────────────────────────────────


def run_predict(
    spec: BoltzPredictSpec,
    artifacts_dir: str | None = None,
    device: str | None = None,
    timeout_s: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute the boltz predict workflow and return a result summary dict."""

    # Resolve device
    resolved_device = device or spec.execution.device or detect_device()

    # Resolve output directory
    if artifacts_dir:
        out_dir = ensure_dir(artifacts_dir, "artifacts directory", create=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="boltz_"))

    # Translate to upstream YAML
    upstream_yaml = translate_to_upstream_yaml(spec)

    # Write upstream YAML to temp file
    yaml_path = out_dir / "boltz_input.yaml"
    yaml_path.write_text(yaml.dump(upstream_yaml, sort_keys=False, default_flow_style=False))

    # Build command
    cmd: list[str] = ["boltz", "predict", str(yaml_path)]
    cmd.extend(["--out_dir", str(out_dir)])

    # MSA options
    if spec.msa.use_server:
        cmd.append("--use_msa_server")
    if spec.msa.msa_dir:
        msa_path = ensure_dir(spec.msa.msa_dir, "MSA directory")
        cmd.extend(["--msa_dir", str(msa_path)])

    # Accelerator
    if resolved_device.startswith("cuda"):
        cmd.extend(["--accelerator", "gpu"])
    else:
        cmd.extend(["--accelerator", "cpu"])

    # Execution parameters
    if spec.execution.recycling_steps is not None:
        cmd.extend(["--recycling_steps", str(spec.execution.recycling_steps)])
    if spec.execution.diffusion_samples is not None:
        cmd.extend(["--diffusion_samples", str(spec.execution.diffusion_samples)])
    if spec.execution.seed is not None:
        cmd.extend(["--seed", str(spec.execution.seed)])

    # Output format
    cmd.extend(["--output_format", "pdb"])

    if dry_run:
        return {
            "dryRun": True,
            "command": cmd,
            "upstreamYaml": upstream_yaml,
            "outputDir": str(out_dir),
        }

    # Execute
    run_result = run_subprocess(cmd, timeout_s=timeout_s, cwd=str(out_dir))

    if run_result.returncode != 0:
        raise UpstreamError(
            f"boltz predict exited with code {run_result.returncode}.\n"
            f"stderr: {run_result.stderr[:2000]}"
        )

    # Parse outputs
    result_summary: dict[str, Any] = {
        "command": cmd,
        "outputDir": str(out_dir),
        "elapsedSeconds": round(run_result.elapsed_seconds, 3),
    }

    # Locate structure files
    predictions_dir = _find_predictions_dir(out_dir)
    if predictions_dir:
        # Confidence JSON
        confidence_files = sorted(predictions_dir.glob("confidence_*_model_0.json"))
        if confidence_files:
            result_summary["confidence"] = parse_confidence_json(confidence_files[0])

        # Affinity JSON
        affinity_files = sorted(predictions_dir.glob("affinity_*.json"))
        if affinity_files:
            result_summary["affinity"] = parse_affinity_json(affinity_files[0])

        # Primary complex structure
        structure_files = sorted(predictions_dir.glob("*_model_0.pdb"))
        if not structure_files:
            structure_files = sorted(predictions_dir.glob("*_model_0.cif"))
        if structure_files:
            result_summary["primaryComplexPath"] = str(structure_files[0])

        # Collect all structure paths
        all_structures = sorted(predictions_dir.glob("*_model_*.pdb"))
        if not all_structures:
            all_structures = sorted(predictions_dir.glob("*_model_*.cif"))
        if all_structures:
            result_summary["structurePaths"] = [str(s) for s in all_structures]

    return result_summary


# ── Output parsers ──────────────────────────────────────────────────────────


def parse_confidence_json(path: Path) -> dict[str, Any]:
    """Parse a Boltz confidence JSON file and return a summary dict."""
    path = Path(path)
    if not path.is_file():
        return {"error": f"Confidence file not found: {path}"}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return {"error": f"Failed to parse confidence JSON: {exc}"}

    # Extract key confidence metrics
    result: dict[str, Any] = {"path": str(path)}
    for key in ("confidence", "ptm", "iptm", "complex_plddt", "complex_iplddt",
                "pair_chains_iptm", "ranking_score"):
        if key in data:
            result[key] = data[key]
    return result


def parse_affinity_json(path: Path) -> dict[str, Any]:
    """Parse a Boltz affinity JSON file and return binderProbability and affinityValue."""
    path = Path(path)
    if not path.is_file():
        return {"error": f"Affinity file not found: {path}"}
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        return {"error": f"Failed to parse affinity JSON: {exc}"}

    result: dict[str, Any] = {"path": str(path)}

    # Boltz affinity output may use various key names; normalise
    binder_prob = data.get("binder_probability") or data.get("binderProbability")
    affinity_val = data.get("affinity_value") or data.get("affinityValue") or data.get("affinity")

    if binder_prob is not None:
        result["binderProbability"] = float(binder_prob)
    if affinity_val is not None:
        result["affinityValue"] = float(affinity_val)

    return result


# ── Helpers ─────────────────────────────────────────────────────────────────


def check_installed() -> bool:
    """Return True if the boltz CLI is available on PATH."""
    return shutil.which("boltz") is not None


def _read_fasta_sequence(path: Path) -> str:
    """Read the first sequence from a FASTA file, stripping headers and whitespace."""
    lines: list[str] = []
    started = False
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith(">"):
            if started:
                break  # next record
            started = True
            continue
        if started:
            lines.append(line)
    seq = "".join(lines)
    if not seq:
        raise ValidationError(f"No sequence found in FASTA file: {path}")
    return seq


def _find_predictions_dir(out_dir: Path) -> Path | None:
    """Locate the Boltz predictions subdirectory under the output dir.

    Boltz typically writes to <out_dir>/boltz_results_<name>/predictions/<name>/
    We walk down to find the deepest predictions subfolder.
    """
    # Look for a predictions directory
    for candidate in sorted(out_dir.rglob("predictions")):
        if candidate.is_dir():
            # Boltz nests another level with the input name
            subdirs = [d for d in candidate.iterdir() if d.is_dir()]
            if subdirs:
                return subdirs[0]
            return candidate
    # Fallback: just use out_dir itself
    return out_dir
