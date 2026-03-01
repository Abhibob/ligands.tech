"""bind-gnina CLI: molecular docking, scoring, and minimization via gnina."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError
from bind_tools.common.runner import detect_device

from .models import (
    GninaDockRequest,
    GninaDockSpec,
    GninaExecution,
    GninaLigand,
    GninaMinimizeRequest,
    GninaMinimizeSpec,
    GninaPose,
    GninaResult,
    GninaResultSummary,
    GninaScoreRequest,
    GninaScoreSpec,
    GninaSearchSpace,
)
from .runner import DOCKER_IMAGE, check_installed, run_gnina_dispatch

app = typer.Typer(name="bind-gnina", help="Molecular docking, scoring, and minimization via gnina.")


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_search_space(
    autobox_ligand: str | None,
    center_x: float | None,
    center_y: float | None,
    center_z: float | None,
    size_x: float | None,
    size_y: float | None,
    size_z: float | None,
) -> GninaSearchSpace:
    """Build a GninaSearchSpace from CLI flags."""
    return GninaSearchSpace(
        autoboxLigandPath=autobox_ligand,
        centerX=center_x,
        centerY=center_y,
        centerZ=center_z,
        sizeX=size_x,
        sizeY=size_y,
        sizeZ=size_z,
    )


def _build_execution(
    cnn_scoring: str,
    num_modes: int,
    exhaustiveness: int,
    seed: int | None,
    pose_sort_order: str,
) -> GninaExecution:
    """Build a GninaExecution from CLI flags."""
    return GninaExecution(
        cnnScoring=cnn_scoring,
        numModes=num_modes,
        exhaustiveness=exhaustiveness,
        seed=seed,
        poseSortOrder=pose_sort_order,
    )


def _build_ligands(ligand: list[str] | None) -> list[GninaLigand]:
    """Build GninaLigand list from --ligand flag values.

    Each value can be a file path (SDF or MOL2) or a SMILES string.
    """
    if not ligand:
        return []
    ligands: list[GninaLigand] = []
    for i, val in enumerate(ligand):
        p = Path(val)
        if p.suffix.lower() in (".sdf", ".sdf.gz"):
            ligands.append(GninaLigand(id=f"lig{i}", sdfPath=val))
        elif p.suffix.lower() in (".mol2",):
            ligands.append(GninaLigand(id=f"lig{i}", mol2Path=val))
        else:
            # Treat as SMILES
            ligands.append(GninaLigand(id=f"lig{i}", smiles=val))
    return ligands


def _build_result(
    mode: str,
    poses: list[GninaPose],
    pose_sort_order: str,
    elapsed: float,
) -> GninaResult:
    """Build the GninaResult envelope from docking poses."""
    summary = GninaResultSummary(
        mode=mode,
        numPoses=len(poses),
        poseSortOrder=pose_sort_order,
        topPose=poses[0] if poses else None,
        poses=poses,
    )
    result = GninaResult()
    result.summary = summary.model_dump(by_alias=True, mode="json")
    result.runtime_seconds = round(elapsed, 3)
    result.status = "succeeded"
    return result


# ── Dock command ─────────────────────────────────────────────────────────────


@app.command()
def dock(
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    receptor: str = typer.Option(None, "--receptor", help="Receptor PDB/PDBQT file"),
    ligand: list[str] = typer.Option(None, "--ligand", help="Ligand file(s) or SMILES (repeatable)"),
    ligand_dir: str = typer.Option(None, "--ligand-dir", help="Directory of SDF/MOL2 ligand files (alternative to --ligand)"),
    autobox_ligand: str = typer.Option(None, "--autobox-ligand", help="Reference ligand for autobox"),
    center_x: float = typer.Option(None, "--center-x", help="Search space center X"),
    center_y: float = typer.Option(None, "--center-y", help="Search space center Y"),
    center_z: float = typer.Option(None, "--center-z", help="Search space center Z"),
    size_x: float = typer.Option(None, "--size-x", help="Search space size X"),
    size_y: float = typer.Option(None, "--size-y", help="Search space size Y"),
    size_z: float = typer.Option(None, "--size-z", help="Search space size Z"),
    cnn_scoring: str = typer.Option("rescore", "--cnn-scoring", help="CNN scoring mode: none|rescore|refinement|all"),
    num_modes: int = typer.Option(9, "--num-modes", help="Max number of binding modes"),
    exhaustiveness: int = typer.Option(8, "--exhaustiveness", help="Search exhaustiveness"),
    scoring: str = typer.Option("vina", "--scoring", help="Scoring function: vina|vinardo|ad4_scoring"),
    seed: int = typer.Option(None, "--seed", help="Random seed"),
    pose_sort_order: str = typer.Option("cnnscore", "--pose-sort-order", help="Pose sort: cnnscore|cnnaffinity|energy"),
    top_n: int = typer.Option(None, "--top-n", help="Return only top N results sorted by score (max 100)"),
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output files"),
    device: str = typer.Option(None, "--device", help="Compute device (cuda:0, cpu)"),
    timeout_s: int = typer.Option(None, "--timeout-s", help="Hard timeout in seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan only"),
    modal: bool = typer.Option(False, "--modal", help="Run on Modal cloud GPU instead of locally"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Run gnina molecular docking."""
    result = GninaResult()
    start = time.monotonic()

    try:
        # Build request from file or flags
        if request or stdin_json:
            req = load_request(request, stdin_json, GninaDockRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not receptor:
                console.print("[red]Provide --receptor or --request[/red]")
                raise typer.Exit(2)
            # Build ligand list from --ligand and --ligand-dir
            all_ligand_paths = list(ligand) if ligand else []
            if ligand_dir:
                from bind_tools.common.batch import glob_input_dir
                dir_files = glob_input_dir(ligand_dir, (".sdf", ".mol2"), "ligand directory")
                all_ligand_paths.extend(str(f) for f in dir_files)

            spec = GninaDockSpec(
                receptorPath=receptor,
                ligands=_build_ligands(all_ligand_paths),
                searchSpace=_build_search_space(
                    autobox_ligand, center_x, center_y, center_z,
                    size_x, size_y, size_z,
                ),
                execution=_build_execution(cnn_scoring, num_modes, exhaustiveness, seed, pose_sort_order),
                scoring=scoring,
            )

        resolved_device = device or detect_device()
        art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "gnina_artifacts"

        if verbose and not quiet:
            console.print(f"[dim]Device: {resolved_device}[/dim]")
            console.print(f"[dim]Receptor: {spec.receptor_path}[/dim]")
            console.print(f"[dim]Ligands: {len(spec.ligands)}[/dim]")

        poses, run_result = run_gnina_dispatch(
            mode="dock",
            spec=spec,
            device=resolved_device,
            artifacts_dir=art_dir,
            timeout_s=timeout_s,
            dry_run=dry_run,
            use_modal=modal,
        )

        if dry_run:
            result.status = "succeeded"
            result.summary = {"dryRun": True, "command": cmd_preview if 'cmd_preview' in dir() else None}
            result.inputs_resolved = {"receptorPath": spec.receptor_path, "ligandCount": len(spec.ligands)}
            result.parameters_resolved = {"mode": "dock", "device": resolved_device}
            result.runtime_seconds = round(time.monotonic() - start, 3)
            write_result(result, json_out, yaml_out)
            raise typer.Exit(0)

        # Apply top-N truncation
        total_poses_count = len(poses)
        if top_n is not None:
            effective_top_n = min(top_n, 100)
            poses = poses[:effective_top_n]

        result = _build_result("dock", poses, spec.execution.pose_sort_order, time.monotonic() - start)
        result.artifacts = {"outputSdf": str(art_dir / "gnina_dock_output.sdf")}
        # Store inputs so the hypothesis tracker can attribute scores to ligands.
        ligand_paths = [l.sdf_path or l.mol2_path or l.smiles or "" for l in spec.ligands]
        result.inputs_resolved = {
            "receptorPath": spec.receptor_path,
            "ligandCount": len(spec.ligands),
            "ligand": ligand_paths[0] if len(ligand_paths) == 1 else None,
            "ligandPaths": ligand_paths,
        }

        if run_result:
            result.provenance = {"dockerImage": DOCKER_IMAGE, "command": " ".join(run_result.command)}

        # Write manifest when using directory input or top-n
        if ligand_dir or top_n:
            from bind_tools.common.manifest import write_manifest
            manifest_path = art_dir / "MANIFEST.md"
            write_manifest(
                path=manifest_path,
                title="bind-gnina dock — Docking Results",
                columns=["Rank", "Ligand", "CNN Score", "CNN Affinity", "Energy (kcal/mol)", "Path"],
                rows=[
                    [
                        str(i + 1),
                        Path(p.path).stem if p.path else f"lig{i}",
                        f"{p.cnn_pose_score:.4f}",
                        f"{p.cnn_affinity:.3f}",
                        f"{p.energy_kcal_mol:.2f}",
                        p.path or "",
                    ]
                    for i, p in enumerate(poses)
                ],
                metadata={
                    "Receptor": spec.receptor_path or "",
                    "Total poses": str(total_poses_count),
                    "Top N shown": str(len(poses)),
                    "Sort order": spec.execution.pose_sort_order,
                },
                summary_lines=[
                    f"Total poses generated: {total_poses_count}",
                    f"Shown: {len(poses)}",
                ],
            )
            result.artifacts["manifestPath"] = str(manifest_path)

        if not quiet:
            console.print(f"[green]Docking complete: {len(poses)} poses generated[/green]")
            if poses:
                top = poses[0]
                console.print(
                    f"  Top pose: energy={top.energy_kcal_mol} kcal/mol, "
                    f"CNNscore={top.cnn_pose_score}, CNNaffinity={top.cnn_affinity}"
                )

    except typer.Exit:
        raise
    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]{exc}[/red]")
    except Exception as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Unexpected error: {exc}[/red]")

    result.runtime_seconds = round(time.monotonic() - start, 3)
    write_result(result, json_out, yaml_out)


# ── Score command ────────────────────────────────────────────────────────────


@app.command()
def score(
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    receptor: str = typer.Option(None, "--receptor", help="Receptor PDB/PDBQT file"),
    ligand: list[str] = typer.Option(None, "--ligand", help="Ligand file(s) (repeatable)"),
    autobox_ligand: str = typer.Option(None, "--autobox-ligand", help="Reference ligand for autobox"),
    center_x: float = typer.Option(None, "--center-x", help="Search space center X"),
    center_y: float = typer.Option(None, "--center-y", help="Search space center Y"),
    center_z: float = typer.Option(None, "--center-z", help="Search space center Z"),
    size_x: float = typer.Option(None, "--size-x", help="Search space size X"),
    size_y: float = typer.Option(None, "--size-y", help="Search space size Y"),
    size_z: float = typer.Option(None, "--size-z", help="Search space size Z"),
    cnn_scoring: str = typer.Option("rescore", "--cnn-scoring", help="CNN scoring mode: none|rescore|refinement|all"),
    num_modes: int = typer.Option(9, "--num-modes", help="Max number of binding modes"),
    exhaustiveness: int = typer.Option(8, "--exhaustiveness", help="Search exhaustiveness"),
    seed: int = typer.Option(None, "--seed", help="Random seed"),
    pose_sort_order: str = typer.Option("cnnscore", "--pose-sort-order", help="Pose sort: cnnscore|cnnaffinity|energy"),
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output files"),
    device: str = typer.Option(None, "--device", help="Compute device (cuda:0, cpu)"),
    timeout_s: int = typer.Option(None, "--timeout-s", help="Hard timeout in seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan only"),
    modal: bool = typer.Option(False, "--modal", help="Run on Modal cloud GPU instead of locally"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Score existing poses with gnina (no docking)."""
    result = GninaResult()
    start = time.monotonic()

    try:
        if request or stdin_json:
            req = load_request(request, stdin_json, GninaScoreRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not receptor:
                console.print("[red]Provide --receptor or --request[/red]")
                raise typer.Exit(2)
            spec = GninaScoreSpec(
                receptorPath=receptor,
                ligands=_build_ligands(ligand),
                searchSpace=_build_search_space(
                    autobox_ligand, center_x, center_y, center_z,
                    size_x, size_y, size_z,
                ),
                execution=_build_execution(cnn_scoring, num_modes, exhaustiveness, seed, pose_sort_order),
            )

        resolved_device = device or detect_device()
        art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "gnina_artifacts"

        if verbose and not quiet:
            console.print(f"[dim]Device: {resolved_device}[/dim]")
            console.print(f"[dim]Receptor: {spec.receptor_path}[/dim]")
            console.print(f"[dim]Ligands: {len(spec.ligands)}[/dim]")

        poses, run_result = run_gnina_dispatch(
            mode="score",
            spec=spec,
            device=resolved_device,
            artifacts_dir=art_dir,
            timeout_s=timeout_s,
            dry_run=dry_run,
            use_modal=modal,
        )

        if dry_run:
            result.status = "succeeded"
            result.summary = {"dryRun": True}
            result.inputs_resolved = {"receptorPath": spec.receptor_path, "ligandCount": len(spec.ligands)}
            result.parameters_resolved = {"mode": "score", "device": resolved_device}
            result.runtime_seconds = round(time.monotonic() - start, 3)
            write_result(result, json_out, yaml_out)
            raise typer.Exit(0)

        result = _build_result("score", poses, spec.execution.pose_sort_order, time.monotonic() - start)
        ligand_paths = [l.sdf_path or l.mol2_path or l.smiles or "" for l in spec.ligands]
        result.inputs_resolved = {
            "receptorPath": spec.receptor_path,
            "ligandCount": len(spec.ligands),
            "ligand": ligand_paths[0] if len(ligand_paths) == 1 else None,
            "ligandPaths": ligand_paths,
        }

        if run_result:
            result.provenance = {"dockerImage": DOCKER_IMAGE, "command": " ".join(run_result.command)}

        if not quiet:
            console.print(f"[green]Scoring complete: {len(poses)} poses scored[/green]")
            if poses:
                top = poses[0]
                console.print(
                    f"  Top pose: energy={top.energy_kcal_mol} kcal/mol, "
                    f"CNNscore={top.cnn_pose_score}, CNNaffinity={top.cnn_affinity}"
                )

    except typer.Exit:
        raise
    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]{exc}[/red]")
    except Exception as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Unexpected error: {exc}[/red]")

    result.runtime_seconds = round(time.monotonic() - start, 3)
    write_result(result, json_out, yaml_out)


# ── Minimize command ─────────────────────────────────────────────────────────


@app.command()
def minimize(
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    receptor: str = typer.Option(None, "--receptor", help="Receptor PDB/PDBQT file"),
    ligand: list[str] = typer.Option(None, "--ligand", help="Ligand file(s) (repeatable)"),
    autobox_ligand: str = typer.Option(None, "--autobox-ligand", help="Reference ligand for autobox"),
    center_x: float = typer.Option(None, "--center-x", help="Search space center X"),
    center_y: float = typer.Option(None, "--center-y", help="Search space center Y"),
    center_z: float = typer.Option(None, "--center-z", help="Search space center Z"),
    size_x: float = typer.Option(None, "--size-x", help="Search space size X"),
    size_y: float = typer.Option(None, "--size-y", help="Search space size Y"),
    size_z: float = typer.Option(None, "--size-z", help="Search space size Z"),
    cnn_scoring: str = typer.Option("rescore", "--cnn-scoring", help="CNN scoring mode: none|rescore|refinement|all"),
    num_modes: int = typer.Option(9, "--num-modes", help="Max number of binding modes"),
    exhaustiveness: int = typer.Option(8, "--exhaustiveness", help="Search exhaustiveness"),
    seed: int = typer.Option(None, "--seed", help="Random seed"),
    pose_sort_order: str = typer.Option("cnnscore", "--pose-sort-order", help="Pose sort: cnnscore|cnnaffinity|energy"),
    minimize_iters: int = typer.Option(0, "--minimize-iters", help="Number of minimize iterations"),
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output files"),
    device: str = typer.Option(None, "--device", help="Compute device (cuda:0, cpu)"),
    timeout_s: int = typer.Option(None, "--timeout-s", help="Hard timeout in seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan only"),
    modal: bool = typer.Option(False, "--modal", help="Run on Modal cloud GPU instead of locally"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Minimize poses with gnina."""
    result = GninaResult()
    start = time.monotonic()

    try:
        if request or stdin_json:
            req = load_request(request, stdin_json, GninaMinimizeRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not receptor:
                console.print("[red]Provide --receptor or --request[/red]")
                raise typer.Exit(2)
            spec = GninaMinimizeSpec(
                receptorPath=receptor,
                ligands=_build_ligands(ligand),
                searchSpace=_build_search_space(
                    autobox_ligand, center_x, center_y, center_z,
                    size_x, size_y, size_z,
                ),
                execution=_build_execution(cnn_scoring, num_modes, exhaustiveness, seed, pose_sort_order),
                minimizeIters=minimize_iters,
            )

        resolved_device = device or detect_device()
        art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "gnina_artifacts"

        if verbose and not quiet:
            console.print(f"[dim]Device: {resolved_device}[/dim]")
            console.print(f"[dim]Receptor: {spec.receptor_path}[/dim]")
            console.print(f"[dim]Ligands: {len(spec.ligands)}[/dim]")
            console.print(f"[dim]Minimize iters: {spec.minimize_iters}[/dim]")

        poses, run_result = run_gnina_dispatch(
            mode="minimize",
            spec=spec,
            device=resolved_device,
            artifacts_dir=art_dir,
            timeout_s=timeout_s,
            dry_run=dry_run,
            use_modal=modal,
        )

        if dry_run:
            result.status = "succeeded"
            result.summary = {"dryRun": True}
            result.inputs_resolved = {"receptorPath": spec.receptor_path, "ligandCount": len(spec.ligands)}
            result.parameters_resolved = {"mode": "minimize", "device": resolved_device}
            result.runtime_seconds = round(time.monotonic() - start, 3)
            write_result(result, json_out, yaml_out)
            raise typer.Exit(0)

        result = _build_result("minimize", poses, spec.execution.pose_sort_order, time.monotonic() - start)
        result.artifacts = {"outputSdf": str(art_dir / "gnina_minimize_output.sdf")}
        ligand_paths = [l.sdf_path or l.mol2_path or l.smiles or "" for l in spec.ligands]
        result.inputs_resolved = {
            "receptorPath": spec.receptor_path,
            "ligandCount": len(spec.ligands),
            "ligand": ligand_paths[0] if len(ligand_paths) == 1 else None,
            "ligandPaths": ligand_paths,
        }

        if run_result:
            result.provenance = {"dockerImage": DOCKER_IMAGE, "command": " ".join(run_result.command)}

        if not quiet:
            console.print(f"[green]Minimization complete: {len(poses)} poses minimized[/green]")
            if poses:
                top = poses[0]
                console.print(
                    f"  Top pose: energy={top.energy_kcal_mol} kcal/mol, "
                    f"CNNscore={top.cnn_pose_score}, CNNaffinity={top.cnn_affinity}"
                )

    except typer.Exit:
        raise
    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]{exc}[/red]")
    except Exception as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Unexpected error: {exc}[/red]")

    result.runtime_seconds = round(time.monotonic() - start, 3)
    write_result(result, json_out, yaml_out)


# ── Doctor command ───────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Check environment for bind-gnina."""
    console.print("[bold]bind-gnina doctor[/bold]")

    # Check Docker
    docker_bin = shutil.which("docker")
    if docker_bin:
        console.print(f"  [green]OK[/green] Docker found: {docker_bin}")
    else:
        console.print("  [red]FAIL[/red] Docker not found in PATH")

    # Check gnina image
    if check_installed():
        console.print(f"  [green]OK[/green] gnina image found: {DOCKER_IMAGE}")
    else:
        if docker_bin:
            console.print(f"  [red]FAIL[/red] gnina image not found: {DOCKER_IMAGE}")
            console.print(f"         Pull it with: docker pull {DOCKER_IMAGE}")
        else:
            console.print(f"  [yellow]SKIP[/yellow] Cannot check gnina image without Docker")

    # Check RDKit (optional, for SDF parsing)
    try:
        import rdkit

        version = getattr(rdkit, "__version__", "unknown")
        console.print(f"  [green]OK[/green] RDKit available: {version}")
    except ImportError:
        console.print("  [yellow]WARN[/yellow] RDKit not installed (fallback SDF parser will be used)")

    # Device detection
    from bind_tools.common.runner import detect_device

    dev = detect_device()
    console.print(f"  [green]OK[/green] Default device: {dev}")


# ── Schema command ───────────────────────────────────────────────────────────


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema([
        "GninaDockRequest",
        "GninaScoreRequest",
        "GninaMinimizeRequest",
        "GninaResult",
    ])


if __name__ == "__main__":
    app()
