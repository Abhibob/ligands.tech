"""bind-posebusters CLI: validate docked poses with PoseBusters."""

from __future__ import annotations

import time

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError

from .models import (
    PoseBustersCheckRequest,
    PoseBustersCheckResult,
    PoseBustersCheckSpec,
    PoseBustersPerformance,
)
from .runner import check_installed, get_version, run_check

app = typer.Typer(
    name="bind-posebusters",
    help="Validate docked poses using PoseBusters quality checks.",
)


@app.command()
def check(
    pred: list[str] = typer.Option(None, "--pred", help="Predicted pose file(s) (repeatable)"),
    pred_dir: str = typer.Option(None, "--pred-dir", help="Directory of predicted pose files (alternative to --pred)"),
    protein: str = typer.Option(None, "--protein", help="Protein structure file (PDB/mmCIF)"),
    reference_ligand: str = typer.Option(None, "--reference-ligand", help="Reference ligand file (SDF/MOL2)"),
    config: str = typer.Option("auto", "--config", help="PoseBusters config: auto|mol|dock|redock"),
    full_report: bool = typer.Option(False, "--full-report", help="Include full check report"),
    top_n: int = typer.Option(None, "--top-n", help="Only check top N poses"),
    max_workers: int = typer.Option(None, "--max-workers", help="Max parallel workers"),
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON request from stdin"),
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs and print plan, don't execute"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Run PoseBusters quality checks on predicted poses."""
    result = PoseBustersCheckResult()
    start = time.monotonic()

    try:
        # Load from request file or flags
        if request or stdin_json:
            req = load_request(request, stdin_json, PoseBustersCheckRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            # Combine --pred and --pred-dir
            all_preds = list(pred) if pred else []
            if pred_dir:
                from bind_tools.common.batch import glob_input_dir
                dir_files = glob_input_dir(pred_dir, (".pdb", ".cif"), "prediction directory")
                all_preds.extend(str(f) for f in dir_files)

            if not all_preds:
                console.print("[red]Provide --pred, --pred-dir, or --request[/red]")
                raise typer.Exit(2)

            pred = all_preds

            performance = PoseBustersPerformance(
                topN=top_n,
                maxWorkers=max_workers,
            )
            spec = PoseBustersCheckSpec(
                predictedPoses=pred,
                proteinPath=protein,
                referenceLigandPath=reference_ligand,
                config=config,
                fullReport=full_report,
                performance=performance,
            )

        # Record resolved inputs
        result.inputs_resolved = {
            "predictedPoses": spec.predicted_poses,
            "proteinPath": spec.protein_path,
            "referenceLigandPath": spec.reference_ligand_path,
        }
        result.parameters_resolved = {
            "config": spec.config,
            "fullReport": spec.full_report,
            "topN": spec.performance.top_n,
            "maxWorkers": spec.performance.max_workers,
            "chunkSize": spec.performance.chunk_size,
        }

        if dry_run:
            console.print(
                f"[yellow]Dry run: would check {len(spec.predicted_poses)} pose(s) "
                f"with config={spec.config}[/yellow]"
            )
            if spec.protein_path:
                console.print(f"  protein: {spec.protein_path}")
            if spec.reference_ligand_path:
                console.print(f"  reference ligand: {spec.reference_ligand_path}")
            raise typer.Exit(0)

        # Apply topN filter
        if spec.performance.top_n is not None and spec.performance.top_n > 0:
            spec = spec.model_copy(
                update={"predicted_poses": spec.predicted_poses[: spec.performance.top_n]}
            )

        # Run checks
        if not quiet:
            console.print(
                f"[bold]Running PoseBusters ({spec.config}) on "
                f"{len(spec.predicted_poses)} pose(s)...[/bold]"
            )

        summaries = run_check(spec)

        # Build summary
        total_poses = len(summaries)
        passed_poses = sum(1 for s in summaries if s.passes_all_checks)
        avg_pass_fraction = (
            sum(s.pass_fraction for s in summaries) / total_poses if total_poses > 0 else 0.0
        )

        result.summary = {
            "totalPoses": total_poses,
            "passedPoses": passed_poses,
            "failedPoses": total_poses - passed_poses,
            "averagePassFraction": round(avg_pass_fraction, 4),
            "poses": [s.model_dump(by_alias=True, mode="json") for s in summaries],
        }
        result.status = "succeeded"

        # Record tool version
        result.tool_version = get_version()

        # Write manifest when using directory input
        if pred_dir:
            from pathlib import Path
            from bind_tools.common.manifest import write_manifest
            # Sort summaries by pass fraction descending
            sorted_summaries = sorted(summaries, key=lambda s: s.pass_fraction, reverse=True)
            manifest_path = Path(pred_dir) / "MANIFEST_posebusters.md"
            write_manifest(
                path=manifest_path,
                title="bind-posebusters check — Validation Results",
                columns=["Rank", "Complex", "Pass Rate", "Fatal", "Major", "Minor", "Status"],
                rows=[
                    [
                        str(i + 1),
                        Path(s.input_path).name,
                        f"{s.pass_fraction:.1%}",
                        str(len(s.fatal_failures)),
                        str(len(s.major_failures)),
                        str(len(s.minor_failures)),
                        "PASS" if s.passes_all_checks else "FAIL",
                    ]
                    for i, s in enumerate(sorted_summaries)
                ],
                metadata={
                    "Total poses": str(total_poses),
                    "Passed": str(passed_poses),
                    "Failed": str(total_poses - passed_poses),
                    "Avg pass rate": f"{avg_pass_fraction:.1%}",
                },
            )
            result.artifacts = result.artifacts or {}
            result.artifacts["manifestPath"] = str(manifest_path)

        if not quiet:
            console.print(
                f"[green]{passed_poses}/{total_poses} poses passed all checks "
                f"(avg pass fraction: {avg_pass_fraction:.1%})[/green]"
            )
            for s in summaries:
                status_color = "green" if s.passes_all_checks else "red"
                console.print(
                    f"  [{status_color}]{s.input_path}: "
                    f"{'PASS' if s.passes_all_checks else 'FAIL'} "
                    f"({s.pass_fraction:.1%})[/{status_color}]"
                )
                if s.fatal_failures:
                    console.print(f"    fatal: {', '.join(s.fatal_failures)}")
                if s.major_failures:
                    console.print(f"    major: {', '.join(s.major_failures)}")
                if s.minor_failures:
                    console.print(f"    minor: {', '.join(s.minor_failures)}")

    except typer.Exit:
        raise
    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]{exc}[/red]")
    except ImportError as exc:
        result.status = "failed"
        result.errors.append(
            f"posebusters is not installed: {exc}. "
            "Install with: pip install posebusters"
        )
        if not quiet:
            console.print(
                "[red]posebusters is not installed. "
                "Install with: pip install posebusters[/red]"
            )
    except Exception as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Unexpected error: {exc}[/red]")

    result.runtime_seconds = round(time.monotonic() - start, 3)
    write_result(result, json_out, yaml_out)


@app.command()
def doctor() -> None:
    """Check environment for bind-posebusters."""
    console.print("[bold]bind-posebusters doctor[/bold]")

    if check_installed():
        version = get_version()
        console.print(f"  [green]OK[/green] posebusters is installed (version: {version})")
    else:
        console.print("  [red]MISSING[/red] posebusters is not installed")
        console.print("    Install with: pip install posebusters")

    # Check optional dependencies
    try:
        import rdkit

        console.print(f"  [green]OK[/green] rdkit is available")
    except ImportError:
        console.print("  [yellow]WARN[/yellow] rdkit is not installed (required by posebusters)")

    try:
        import pandas

        console.print(f"  [green]OK[/green] pandas is available")
    except ImportError:
        console.print("  [yellow]WARN[/yellow] pandas is not installed (required by posebusters)")


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema(["PoseBustersCheckRequest", "PoseBustersCheckResult"])


if __name__ == "__main__":
    app()
