"""Modal remote class for running Boltz-2 structure prediction on cloud GPUs."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import modal

from ._base import BOLTZ_WEIGHTS_MOUNT, boltz_weights_volume, app
from .file_io import FilePayload
from .images import boltz_image


@app.cls(
    image=boltz_image,
    gpu="A100",
    volumes={BOLTZ_WEIGHTS_MOUNT: boltz_weights_volume},
    timeout=1800,
)
class BoltzPredictor:
    """Runs boltz predict on a Modal A100 GPU."""

    @modal.enter()
    def warmup(self) -> None:
        """Verify the boltz CLI is available inside the container."""
        result = subprocess.run(
            ["boltz", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"boltz CLI not available: {result.stderr[:500]}")

    @modal.method()
    def predict(
        self,
        upstream_yaml: dict[str, Any],
        input_files: list[dict[str, bytes]],
        accelerator: str = "gpu",
        use_msa_server: bool = False,
        msa_dir: str | None = None,
        recycling_steps: int | None = None,
        diffusion_samples: int | None = None,
        seed: int | None = None,
    ) -> dict[str, Any]:
        """Run boltz predict and return output files + parsed results.

        Parameters
        ----------
        upstream_yaml : dict
            The Boltz input YAML dict (our translate_to_upstream_yaml output).
        input_files : list[dict]
            Each dict has keys ``name`` (str) and ``data`` (bytes).
        accelerator : str
            "gpu" or "cpu".
        use_msa_server, msa_dir, recycling_steps, diffusion_samples, seed :
            Forwarded to the boltz CLI.

        Returns
        -------
        dict with keys:
            - ``output_files``: list[dict] with name/data for each output file
            - ``confidence``: parsed confidence dict or None
            - ``affinity``: parsed affinity dict or None
            - ``primary_complex_path``: filename of the primary structure
            - ``structure_filenames``: list of structure file names
            - ``returncode``, ``stdout``, ``stderr``
        """
        import yaml

        work_dir = Path(tempfile.mkdtemp(prefix="boltz_modal_"))

        # Materialise input files
        for fp in input_files:
            dest = work_dir / fp["name"]
            dest.write_bytes(fp["data"])

        # Rewrite file paths in upstream YAML to point at materialised files
        for seq_entry in upstream_yaml.get("sequences", []):
            for kind in ("protein", "ligand"):
                block = seq_entry.get(kind)
                if not block:
                    continue
                for key in ("fasta", "pdb", "cif", "sdf", "mol2"):
                    if key in block and isinstance(block[key], str):
                        fname = Path(block[key]).name
                        block[key] = str(work_dir / fname)

        # Write upstream YAML
        yaml_path = work_dir / "boltz_input.yaml"
        yaml_path.write_text(
            yaml.dump(upstream_yaml, sort_keys=False, default_flow_style=False)
        )

        # Build command
        cmd: list[str] = [
            "boltz", "predict", str(yaml_path),
            "--out_dir", str(work_dir),
            "--accelerator", accelerator,
            "--output_format", "pdb",
        ]
        if use_msa_server:
            cmd.append("--use_msa_server")
        if msa_dir:
            cmd.extend(["--msa_dir", msa_dir])
        if recycling_steps is not None:
            cmd.extend(["--recycling_steps", str(recycling_steps)])
        if diffusion_samples is not None:
            cmd.extend(["--diffusion_samples", str(diffusion_samples)])
        if seed is not None:
            cmd.extend(["--seed", str(seed)])

        # Set cache dir so weights persist in the volume
        import os
        os.environ["BOLTZ_CACHE_DIR"] = BOLTZ_WEIGHTS_MOUNT

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1500,
            cwd=str(work_dir),
        )

        # Commit volume so downloaded weights persist across runs
        boltz_weights_volume.commit()

        # Collect results
        result: dict[str, Any] = {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-5000:] if proc.stdout else "",
            "stderr": proc.stderr[-5000:] if proc.stderr else "",
            "output_files": [],
            "confidence": None,
            "affinity": None,
            "primary_complex_path": None,
            "structure_filenames": [],
        }

        if proc.returncode != 0:
            return result

        # Find predictions directory
        predictions_dir = _find_predictions_dir(work_dir)
        if not predictions_dir:
            return result

        # Parse confidence
        conf_files = sorted(predictions_dir.glob("confidence_*_model_0.json"))
        if conf_files:
            result["confidence"] = _parse_json_file(conf_files[0])
            result["output_files"].append(
                {"name": conf_files[0].name, "data": conf_files[0].read_bytes()}
            )

        # Parse affinity
        aff_files = sorted(predictions_dir.glob("affinity_*.json"))
        if aff_files:
            result["affinity"] = _parse_json_file(aff_files[0])
            result["output_files"].append(
                {"name": aff_files[0].name, "data": aff_files[0].read_bytes()}
            )

        # Collect structure files
        structures = sorted(predictions_dir.glob("*_model_*.pdb"))
        if not structures:
            structures = sorted(predictions_dir.glob("*_model_*.cif"))

        for s in structures:
            result["output_files"].append(
                {"name": s.name, "data": s.read_bytes()}
            )
            result["structure_filenames"].append(s.name)

        if structures:
            result["primary_complex_path"] = structures[0].name

        return result


def _find_predictions_dir(out_dir: Path) -> Path | None:
    """Locate the Boltz predictions subdirectory."""
    for candidate in sorted(out_dir.rglob("predictions")):
        if candidate.is_dir():
            subdirs = [d for d in candidate.iterdir() if d.is_dir()]
            if subdirs:
                return subdirs[0]
            return candidate
    return out_dir


def _parse_json_file(path: Path) -> dict[str, Any] | None:
    """Safely parse a JSON file."""
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
