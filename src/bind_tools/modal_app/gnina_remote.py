"""Modal remote class for running GNINA molecular docking on cloud GPUs."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Any

import modal

from ._base import app
from .images import gnina_image


@app.cls(
    image=gnina_image,
    gpu="T4",
    timeout=600,
)
class GninaRunner:
    """Runs gnina on a Modal T4 GPU."""

    @modal.enter()
    def warmup(self) -> None:
        """Verify gnina binary is available inside the container."""
        result = subprocess.run(
            ["gnina", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode not in (0, 1):
            # gnina --help may return 1 but still work
            raise RuntimeError(f"gnina binary not available: {result.stderr[:500]}")

    @modal.method()
    def run(
        self,
        mode: str,
        gnina_args: list[str],
        input_files: list[dict[str, bytes]],
        output_filename: str | None = None,
    ) -> dict[str, Any]:
        """Run gnina and return stdout/stderr + output file bytes.

        Parameters
        ----------
        mode : str
            "dock", "score", or "minimize".
        gnina_args : list[str]
            Pre-built gnina CLI args (using filenames, not container paths).
        input_files : list[dict]
            Each dict has keys ``name`` (str) and ``data`` (bytes).
        output_filename : str or None
            Expected output SDF filename (None for score mode).

        Returns
        -------
        dict with keys:
            - ``returncode``, ``stdout``, ``stderr``
            - ``output_file``: dict with name/data if an SDF was produced, else None
        """
        work_dir = Path(tempfile.mkdtemp(prefix="gnina_modal_"))

        # Materialise input files
        for fp in input_files:
            dest = work_dir / fp["name"]
            dest.write_bytes(fp["data"])

        # Rewrite gnina_args: replace bare filenames with full paths
        resolved_args: list[str] = []
        # Flags whose next argument is a filename
        _FILE_FLAGS = {"-r", "-l", "--autobox_ligand", "-o"}
        i = 0
        while i < len(gnina_args):
            arg = gnina_args[i]
            if arg in _FILE_FLAGS and i + 1 < len(gnina_args):
                resolved_args.append(arg)
                fname = gnina_args[i + 1]
                candidate = work_dir / fname
                if candidate.exists():
                    resolved_args.append(str(candidate))
                else:
                    resolved_args.append(fname)
                i += 2
            else:
                resolved_args.append(arg)
                i += 1

        # If output_filename, ensure it points into work_dir
        if output_filename:
            out_path = work_dir / output_filename
            # Replace -o value in resolved_args
            for idx, a in enumerate(resolved_args):
                if a == "-o" and idx + 1 < len(resolved_args):
                    resolved_args[idx + 1] = str(out_path)
                    break

        cmd = ["gnina"] + resolved_args

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=500,
            cwd=str(work_dir),
        )

        result: dict[str, Any] = {
            "returncode": proc.returncode,
            "stdout": proc.stdout[-10000:] if proc.stdout else "",
            "stderr": proc.stderr[-5000:] if proc.stderr else "",
            "output_file": None,
        }

        # Return output SDF if it was produced
        if output_filename:
            out_path = work_dir / output_filename
            if out_path.is_file():
                result["output_file"] = {
                    "name": output_filename,
                    "data": out_path.read_bytes(),
                }

        return result
