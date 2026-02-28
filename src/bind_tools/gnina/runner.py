"""Gnina runner: molecular docking via Docker-wrapped gnina binary."""

from __future__ import annotations

import shutil
from pathlib import Path

from bind_tools.common.cli_base import console
from bind_tools.common.errors import InputMissingError, UpstreamError
from bind_tools.common.runner import ensure_dir, ensure_file, run_docker, RunResult

from .models import (
    GninaDockSpec,
    GninaExecution,
    GninaMinimizeSpec,
    GninaPose,
    GninaScoreSpec,
    GninaSearchSpace,
)

DOCKER_IMAGE = "gnina/gnina:latest"


# ── Docker command building ──────────────────────────────────────────────────


def _resolve_device_flags(device: str) -> list[str]:
    """Return gnina CLI flags for the given device string."""
    if device == "cpu":
        return ["--no_gpu"]
    if device.startswith("cuda:"):
        idx = device.split(":", 1)[1]
        return ["--device", idx]
    # Default: let gnina auto-detect
    return []


def _search_space_flags(ss: GninaSearchSpace, volumes: dict[str, str] | None = None) -> list[str]:
    """Return gnina CLI flags for defining the search space."""
    flags: list[str] = []
    if ss.autobox_ligand_path:
        if volumes:
            container = _container_path(ss.autobox_ligand_path, volumes)
        else:
            container = f"/data/{Path(ss.autobox_ligand_path).name}"
        flags.extend(["--autobox_ligand", container])
    else:
        if ss.center_x is not None:
            flags.extend(["--center_x", str(ss.center_x)])
        if ss.center_y is not None:
            flags.extend(["--center_y", str(ss.center_y)])
        if ss.center_z is not None:
            flags.extend(["--center_z", str(ss.center_z)])
        if ss.size_x is not None:
            flags.extend(["--size_x", str(ss.size_x)])
        if ss.size_y is not None:
            flags.extend(["--size_y", str(ss.size_y)])
        if ss.size_z is not None:
            flags.extend(["--size_z", str(ss.size_z)])
    return flags


def _execution_flags(ex: GninaExecution) -> list[str]:
    """Return gnina CLI flags from execution settings."""
    flags: list[str] = []
    flags.extend(["--cnn_scoring", ex.cnn_scoring])
    if ex.exhaustiveness != 8:
        flags.extend(["--exhaustiveness", str(ex.exhaustiveness)])
    if ex.num_modes != 9:
        flags.extend(["--num_modes", str(ex.num_modes)])
    if ex.seed is not None:
        flags.extend(["--seed", str(ex.seed)])
    if ex.cpu is not None:
        flags.extend(["--cpu", str(ex.cpu)])
    return flags


def _collect_volumes(
    receptor_path: str,
    ligand_paths: list[str],
    autobox_path: str | None,
    output_dir: Path,
) -> dict[str, str]:
    """Build host->container volume mappings for all needed files and dirs.

    Deduplicates directories so the same host dir is only mounted once.
    """
    volumes: dict[str, str] = {}

    # Output directory
    volumes[str(output_dir)] = "/data/output"

    # Collect all unique parent directories that need mounting
    all_dirs: list[str] = []
    all_dirs.append(str(Path(receptor_path).resolve().parent))
    for lp in ligand_paths:
        d = str(Path(lp).resolve().parent)
        if d not in all_dirs:
            all_dirs.append(d)
    if autobox_path:
        d = str(Path(autobox_path).resolve().parent)
        if d not in all_dirs:
            all_dirs.append(d)

    # Assign container mount points, deduplicating
    for i, host_dir in enumerate(all_dirs):
        if host_dir not in volumes:
            volumes[host_dir] = f"/data/inputs{i}"

    return volumes


def _container_path(host_path: str, volumes: dict[str, str]) -> str:
    """Translate a host file path into its container equivalent."""
    resolved = Path(host_path).resolve()
    parent_str = str(resolved.parent)
    for host_dir, container_dir in volumes.items():
        if parent_str == host_dir or parent_str.startswith(host_dir + "/"):
            rel = resolved.relative_to(Path(host_dir))
            return f"{container_dir}/{rel}"
    # Fallback: mount the file's parent
    return f"/data/{resolved.name}"


def build_docker_cmd(
    mode: str,
    spec: GninaDockSpec | GninaScoreSpec | GninaMinimizeSpec,
    output_path: Path,
    device: str,
) -> tuple[list[str], dict[str, str]]:
    """Build the gnina command and volume mappings for Docker execution.

    Returns (cmd, volumes) where cmd is the gnina argument list and volumes
    is the host-to-container mount map.
    """
    # Collect all ligand file paths
    ligand_paths: list[str] = []
    for lig in spec.ligands:
        if lig.sdf_path:
            ligand_paths.append(lig.sdf_path)
        elif lig.mol2_path:
            ligand_paths.append(lig.mol2_path)

    autobox_path = spec.search_space.autobox_ligand_path if spec.search_space else None

    volumes = _collect_volumes(
        spec.receptor_path,
        ligand_paths,
        autobox_path,
        output_path.parent,
    )

    # Build the gnina command (everything after `docker run ... image`)
    cmd: list[str] = ["gnina"]

    # Receptor
    receptor_container = _container_path(spec.receptor_path, volumes)
    cmd.extend(["-r", receptor_container])

    # Ligands
    for lig in spec.ligands:
        if lig.sdf_path:
            cmd.extend(["-l", _container_path(lig.sdf_path, volumes)])
        elif lig.mol2_path:
            cmd.extend(["-l", _container_path(lig.mol2_path, volumes)])
        elif lig.smiles:
            # gnina supports --smiles for inline SMILES
            cmd.extend(["--smiles", lig.smiles])

    # Mode-specific flags
    if mode == "dock":
        dock_spec: GninaDockSpec = spec  # type: ignore[assignment]
        # Search space
        cmd.extend(_search_space_flags(dock_spec.search_space, volumes))
        # Execution
        cmd.extend(_execution_flags(dock_spec.execution))
        # Scoring function
        if dock_spec.scoring != "vina":
            cmd.extend(["--scoring", dock_spec.scoring])
        # Pose sort order
        if dock_spec.execution.pose_sort_order != "cnnscore":
            cmd.extend(["--pose_sort_order", dock_spec.execution.pose_sort_order])
        # Output
        out_container = f"/data/output/{output_path.name}"
        cmd.extend(["-o", out_container])

    elif mode == "score":
        cmd.append("--score_only")
        cmd.extend(_execution_flags(spec.execution))
        if spec.search_space:
            cmd.extend(_search_space_flags(spec.search_space, volumes))

    elif mode == "minimize":
        min_spec: GninaMinimizeSpec = spec  # type: ignore[assignment]
        cmd.append("--minimize")
        cmd.extend(_execution_flags(min_spec.execution))
        if min_spec.search_space:
            cmd.extend(_search_space_flags(min_spec.search_space, volumes))
        if min_spec.minimize_iters > 0:
            cmd.extend(["--minimize_iters", str(min_spec.minimize_iters)])
        # Output
        out_container = f"/data/output/{output_path.name}"
        cmd.extend(["-o", out_container])

    # Device flags
    cmd.extend(_resolve_device_flags(device))

    return cmd, volumes


# ── SDF output parsing ───────────────────────────────────────────────────────


def parse_sdf_output(sdf_path: Path) -> list[GninaPose]:
    """Parse gnina SDF output into a list of GninaPose objects.

    Uses RDKit's SDMolSupplier to read SD properties:
    minimizedAffinity, CNNscore, CNNaffinity.
    """
    try:
        from rdkit.Chem import SDMolSupplier
    except ImportError:
        # Fallback: basic text parsing when RDKit is not available
        return _parse_sdf_fallback(sdf_path)

    poses: list[GninaPose] = []
    supplier = SDMolSupplier(str(sdf_path), removeHs=False)

    for rank_idx, mol in enumerate(supplier):
        if mol is None:
            continue

        energy = 0.0
        cnn_score = 0.0
        cnn_aff = 0.0

        try:
            energy = float(mol.GetProp("minimizedAffinity"))
        except (KeyError, ValueError):
            pass
        try:
            cnn_score = float(mol.GetProp("CNNscore"))
        except (KeyError, ValueError):
            pass
        try:
            cnn_aff = float(mol.GetProp("CNNaffinity"))
        except (KeyError, ValueError):
            pass

        poses.append(
            GninaPose(
                rank=rank_idx + 1,
                energyKcalMol=round(energy, 3),
                cnnPoseScore=round(cnn_score, 4),
                cnnAffinity=round(cnn_aff, 4),
                path=str(sdf_path),
            )
        )

    return poses


def _parse_sdf_fallback(sdf_path: Path) -> list[GninaPose]:
    """Minimal SDF parser when RDKit is not installed.

    Reads SD property fields from the raw text.
    """
    if not sdf_path.is_file():
        return []

    text = sdf_path.read_text()
    blocks = text.split("$$$$")
    poses: list[GninaPose] = []

    for rank_idx, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        energy = 0.0
        cnn_score = 0.0
        cnn_aff = 0.0

        lines = block.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped == "> <minimizedAffinity>" and i + 1 < len(lines):
                try:
                    energy = float(lines[i + 1].strip())
                except ValueError:
                    pass
            elif stripped == "> <CNNscore>" and i + 1 < len(lines):
                try:
                    cnn_score = float(lines[i + 1].strip())
                except ValueError:
                    pass
            elif stripped == "> <CNNaffinity>" and i + 1 < len(lines):
                try:
                    cnn_aff = float(lines[i + 1].strip())
                except ValueError:
                    pass

        poses.append(
            GninaPose(
                rank=rank_idx + 1,
                energyKcalMol=round(energy, 3),
                cnnPoseScore=round(cnn_score, 4),
                cnnAffinity=round(cnn_aff, 4),
                path=str(sdf_path),
            )
        )

    return poses


# ── Main orchestrator ────────────────────────────────────────────────────────


def run_gnina(
    mode: str,
    spec: GninaDockSpec | GninaScoreSpec | GninaMinimizeSpec,
    device: str,
    artifacts_dir: Path,
    timeout_s: int | None = None,
    dry_run: bool = False,
) -> tuple[list[GninaPose], RunResult | None]:
    """Orchestrate a gnina run: build command, run Docker, parse output.

    Returns (poses, run_result). If dry_run is True, returns ([], None).
    """
    # Validate receptor exists
    ensure_file(spec.receptor_path, "receptor")

    # Validate ligand files exist
    for lig in spec.ligands:
        if lig.sdf_path:
            ensure_file(lig.sdf_path, f"ligand SDF ({lig.id or lig.sdf_path})")
        if lig.mol2_path:
            ensure_file(lig.mol2_path, f"ligand MOL2 ({lig.id or lig.mol2_path})")

    # Validate autobox ligand if specified
    if spec.search_space and spec.search_space.autobox_ligand_path:
        ensure_file(spec.search_space.autobox_ligand_path, "autobox ligand")

    # Ensure artifacts directory
    output_dir = ensure_dir(artifacts_dir, "artifacts directory", create=True)
    output_sdf = output_dir / f"gnina_{mode}_output.sdf"

    # Build Docker command
    cmd, volumes = build_docker_cmd(mode, spec, output_sdf, device)

    if dry_run:
        console.print(f"[yellow]Dry run: would execute gnina {mode}[/yellow]")
        console.print(f"[yellow]  Command: {' '.join(cmd)}[/yellow]")
        console.print(f"[yellow]  Volumes: {volumes}[/yellow]")
        return [], None

    # Execute via Docker
    docker_device = "cpu" if device == "cpu" else device
    run_result = run_docker(
        DOCKER_IMAGE,
        cmd,
        volumes=volumes,
        device=docker_device,
        timeout_s=timeout_s,
    )

    if run_result.returncode != 0:
        raise UpstreamError(
            f"gnina exited with code {run_result.returncode}.\n"
            f"stderr: {run_result.stderr[:2000]}"
        )

    # Parse output
    if mode == "score":
        # score_only writes to stdout, not a file
        poses = _parse_score_stdout(run_result.stdout, mode)
    else:
        if not output_sdf.is_file():
            raise UpstreamError(
                f"gnina did not produce expected output file: {output_sdf}"
            )
        poses = parse_sdf_output(output_sdf)

    return poses, run_result


def _parse_score_stdout(stdout: str, mode: str) -> list[GninaPose]:
    """Parse gnina --score_only stdout output.

    gnina score_only prints lines like:
      ## Name Affinity CNNscore CNNaffinity
      ...data lines with numeric values...

    We skip all non-numeric lines and extract values robustly.
    """
    poses: list[GninaPose] = []
    lines = stdout.strip().split("\n")

    # Common gnina info prefixes to skip
    _SKIP_PREFIXES = (
        "#", "Using", "Reading", "WARNING", "NOTE", "CNN",
        "Output", "Refine", "Loading", "Setting", "Parse",
        "Scoring", "Minimiz", "Search",
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(line.startswith(p) for p in _SKIP_PREFIXES):
            continue

        # Try to parse numeric columns; gnina outputs vary but
        # data lines always start with numeric or a name followed by numerics
        parts = line.split()
        # Find the first run of 3 consecutive floats in the parts
        numeric_vals: list[float] = []
        for part in parts:
            try:
                numeric_vals.append(float(part))
            except ValueError:
                numeric_vals = []  # reset on non-numeric

            if len(numeric_vals) >= 3:
                break

        if len(numeric_vals) >= 3:
            energy, cnn_score, cnn_aff = numeric_vals[0], numeric_vals[1], numeric_vals[2]
            poses.append(
                GninaPose(
                    rank=len(poses) + 1,
                    energyKcalMol=round(energy, 3),
                    cnnPoseScore=round(cnn_score, 4),
                    cnnAffinity=round(cnn_aff, 4),
                    path="",
                )
            )

    return poses


# ── Environment check ────────────────────────────────────────────────────────


def check_installed() -> bool:
    """Check if Docker is available and the gnina image exists."""
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return False

    import subprocess

    try:
        result = subprocess.run(
            [docker_bin, "image", "inspect", DOCKER_IMAGE],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return result.returncode == 0
    except Exception:
        return False
