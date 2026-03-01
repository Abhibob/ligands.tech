"""Boltz runner: translate request to upstream YAML, invoke boltz predict, parse outputs."""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

import httpx
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


# ── Modal dispatch ─────────────────────────────────────────────────────────


def run_predict_modal(
    spec: BoltzPredictSpec,
    artifacts_dir: str | None = None,
    timeout_s: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute boltz predict on a Modal cloud GPU and return a result summary dict."""
    from bind_tools.modal_app.file_io import collect_input_files_boltz

    # Translate to upstream YAML
    upstream_yaml = translate_to_upstream_yaml(spec)

    if dry_run:
        return {
            "dryRun": True,
            "command": ["modal", "remote", "boltz", "predict"],
            "upstreamYaml": upstream_yaml,
            "backend": "modal",
        }

    # Collect input files as byte payloads
    input_file_dicts = [
        {"name": fp.name, "data": fp.data}
        for fp in collect_input_files_boltz(upstream_yaml)
    ]

    # Call the Modal remote class
    from bind_tools.modal_app.boltz_remote import BoltzPredictor

    predictor = BoltzPredictor()
    remote_result = predictor.predict.remote(
        upstream_yaml=upstream_yaml,
        input_files=input_file_dicts,
        accelerator="gpu",
        use_msa_server=spec.msa.use_server,
        msa_dir=spec.msa.msa_dir,
        recycling_steps=spec.execution.recycling_steps,
        diffusion_samples=spec.execution.diffusion_samples,
        seed=spec.execution.seed,
    )

    if remote_result["returncode"] != 0:
        raise UpstreamError(
            f"boltz predict (Modal) exited with code {remote_result['returncode']}.\n"
            f"stderr: {remote_result['stderr'][:2000]}"
        )

    # Write output files locally
    if artifacts_dir:
        out_dir = ensure_dir(artifacts_dir, "artifacts directory", create=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="boltz_modal_"))

    from bind_tools.modal_app.file_io import FilePayload, write_file_payload

    for fp_dict in remote_result.get("output_files", []):
        payload = FilePayload(name=fp_dict["name"], data=fp_dict["data"])
        write_file_payload(payload, out_dir)

    # Build result summary matching the shape of run_predict()
    result_summary: dict[str, Any] = {
        "command": ["boltz", "predict", "(modal-remote)"],
        "outputDir": str(out_dir),
        "backend": "modal",
    }

    if remote_result.get("confidence"):
        result_summary["confidence"] = _normalise_confidence(remote_result["confidence"])

    if remote_result.get("affinity"):
        result_summary["affinity"] = _normalise_affinity(remote_result["affinity"])

    if remote_result.get("primary_complex_path"):
        result_summary["primaryComplexPath"] = str(
            out_dir / remote_result["primary_complex_path"]
        )

    if remote_result.get("structure_filenames"):
        result_summary["structurePaths"] = [
            str(out_dir / fn) for fn in remote_result["structure_filenames"]
        ]

    return result_summary


def _normalise_confidence(data: dict[str, Any]) -> dict[str, Any]:
    """Extract key confidence metrics from raw Boltz JSON."""
    result: dict[str, Any] = {}
    for key in ("confidence", "ptm", "iptm", "complex_plddt", "complex_iplddt",
                "pair_chains_iptm", "ranking_score"):
        if key in data:
            result[key] = data[key]
    return result


def _normalise_affinity(data: dict[str, Any]) -> dict[str, Any]:
    """Extract affinity metrics from raw Boltz JSON."""
    result: dict[str, Any] = {}
    binder_prob = data.get("binder_probability") or data.get("binderProbability")
    affinity_val = data.get("affinity_value") or data.get("affinityValue") or data.get("affinity")
    if binder_prob is not None:
        result["binderProbability"] = float(binder_prob)
    if affinity_val is not None:
        result["affinityValue"] = float(affinity_val)
    return result


# ── Remote REST API dispatch ──────────────────────────────────────────────

REMOTE_BASE_URL = "https://benwu408--bind-tools-gpu-webapi-serve.modal.run"


def _collect_input_files_for_remote(upstream_yaml: dict[str, Any]) -> list[dict[str, str]]:
    """Collect input files referenced in the upstream YAML and base64-encode them.

    Scans the sequences list for file-path references (sdf, mol2, fasta) and
    reads + encodes them for the REST API.
    """
    files: list[dict[str, str]] = []
    seen: set[str] = set()

    for seq_entry in upstream_yaml.get("sequences", []):
        for _kind, value in seq_entry.items():
            if not isinstance(value, dict):
                continue
            for file_key in ("sdf", "mol2", "fasta"):
                file_path = value.get(file_key)
                if file_path and file_path not in seen:
                    seen.add(file_path)
                    path = Path(file_path)
                    if path.is_file():
                        encoded = base64.b64encode(path.read_bytes()).decode()
                        files.append({"name": path.name, "data": encoded})
                        # Rewrite the YAML value to use bare filename
                        value[file_key] = path.name

    return files


def run_predict_remote(
    spec: BoltzPredictSpec,
    artifacts_dir: str | None = None,
    timeout_s: int | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Execute boltz predict via the remote REST API and return a result summary dict."""

    api_key = os.environ.get("BIND_TOOLS_API_KEY", "")
    if not api_key:
        raise UpstreamError("BIND_TOOLS_API_KEY environment variable is required for remote execution")

    # Translate to upstream YAML
    upstream_yaml = translate_to_upstream_yaml(spec)

    # Collect and base64-encode input files referenced in the YAML
    input_files = _collect_input_files_for_remote(upstream_yaml)

    if dry_run:
        return {
            "dryRun": True,
            "command": ["remote", "POST", "/v1/boltz/predict"],
            "upstreamYaml": upstream_yaml,
            "backend": "remote",
        }

    # Build request body
    body: dict[str, Any] = {"upstream_yaml": upstream_yaml}
    if input_files:
        body["input_files"] = input_files
    if spec.msa.use_server:
        body["use_msa_server"] = True
    if spec.execution.recycling_steps is not None:
        body["recycling_steps"] = spec.execution.recycling_steps
    if spec.execution.diffusion_samples is not None:
        body["diffusion_samples"] = spec.execution.diffusion_samples
    if spec.execution.seed is not None:
        body["seed"] = spec.execution.seed

    # POST to remote endpoint
    url = f"{REMOTE_BASE_URL}/v1/boltz/predict"
    effective_timeout = timeout_s or 600

    with httpx.Client(timeout=effective_timeout, follow_redirects=True) as client:
        resp = client.post(
            url,
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    if resp.status_code == 401:
        raise UpstreamError("Remote API authentication failed (401). Check BIND_TOOLS_API_KEY.")
    if resp.status_code == 422:
        raise UpstreamError(f"Remote API validation error (422): {resp.text[:2000]}")
    resp.raise_for_status()

    remote_result = resp.json()

    if remote_result.get("returncode", 1) != 0:
        raise UpstreamError(
            f"boltz predict (remote) exited with code {remote_result.get('returncode')}.\n"
            f"stderr: {remote_result.get('stderr', '')[:2000]}"
        )

    # Write output files locally
    if artifacts_dir:
        out_dir = ensure_dir(artifacts_dir, "artifacts directory", create=True)
    else:
        out_dir = Path(tempfile.mkdtemp(prefix="boltz_remote_"))

    for fp in remote_result.get("output_files", []):
        file_path = out_dir / fp["name"]
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(base64.b64decode(fp["data"]))

    # Build result summary matching the shape of run_predict()
    result_summary: dict[str, Any] = {
        "command": ["boltz", "predict", "(remote)"],
        "outputDir": str(out_dir),
        "backend": "remote",
    }

    if remote_result.get("confidence"):
        result_summary["confidence"] = _normalise_confidence(remote_result["confidence"])

    if remote_result.get("affinity"):
        result_summary["affinity"] = _normalise_affinity(remote_result["affinity"])

    if remote_result.get("primary_complex_path"):
        result_summary["primaryComplexPath"] = str(
            out_dir / remote_result["primary_complex_path"]
        )

    if remote_result.get("structure_filenames"):
        result_summary["structurePaths"] = [
            str(out_dir / fn) for fn in remote_result["structure_filenames"]
        ]

    return result_summary


def _is_remote() -> bool:
    """Return True if remote execution is enabled via REMOTE env var."""
    return os.environ.get("REMOTE", "").strip().lower() in ("on", "1", "true")


def run_predict_dispatch(
    spec: BoltzPredictSpec,
    artifacts_dir: str | None = None,
    device: str | None = None,
    timeout_s: int | None = None,
    dry_run: bool = False,
    use_modal: bool = False,
) -> dict[str, Any]:
    """Route to local, Modal, or remote REST API execution."""
    if _is_remote():
        return run_predict_remote(
            spec,
            artifacts_dir=artifacts_dir,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )
    if use_modal or os.environ.get("BIND_TOOLS_USE_MODAL", "").strip() == "1":
        return run_predict_modal(
            spec,
            artifacts_dir=artifacts_dir,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )
    return run_predict(
        spec,
        artifacts_dir=artifacts_dir,
        device=device,
        timeout_s=timeout_s,
        dry_run=dry_run,
    )


# ── Output parsers ──────────────────────────────────────────────────────────


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
