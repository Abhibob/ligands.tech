"""bind-plip CLI: protein-ligand interaction profiling."""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError

from .models import (
    PlipOutputs,
    PlipProfileRequest,
    PlipProfileResult,
    PlipProfileSpec,
    PlipStructureHandling,
)
from .runner import check_installed, check_openbabel_installed, run_profile

app = typer.Typer(name="bind-plip", help="Protein-ligand interaction profiling via PLIP.")


@app.command()
def profile(
    # ── Request loading ──────────────────────────────────────────────────
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    # ── Direct spec flags ────────────────────────────────────────────────
    complex: str = typer.Option(None, "--complex", help="Path to PDB/mmCIF complex file"),
    complex_dir: str = typer.Option(None, "--complex-dir", help="Directory of PDB/CIF complex files to profile"),
    pdb_id: str = typer.Option(None, "--pdb-id", help="4-letter PDB ID to fetch from RCSB"),
    binding_site: str = typer.Option(None, "--binding-site", help="Binding site identifier"),
    model: int = typer.Option(1, "--model", min=1, help="Model number (1-based)"),
    # ── Output format flags ──────────────────────────────────────────────
    txt: bool = typer.Option(False, "--txt", help="Generate text report"),
    xml: bool = typer.Option(False, "--xml", help="Generate XML report"),
    pymol: bool = typer.Option(False, "--pymol", help="Generate PyMOL visualization script"),
    pics: bool = typer.Option(False, "--pics", help="Generate interaction diagrams"),
    # ── Structure handling flags ─────────────────────────────────────────
    nohydro: bool = typer.Option(False, "--nohydro", help="Do not add hydrogens"),
    # ── Batch output ──────────────────────────────────────────────────
    top_n: int = typer.Option(None, "--top-n", help="Return only top N results sorted by interaction count (max 100)"),
    # ── Output envelope ──────────────────────────────────────────────────
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output artifacts"),
    # ── Behavioural flags ────────────────────────────────────────────────
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan, don't execute"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Profile protein-ligand interactions in a PDB complex."""
    result = PlipProfileResult()
    start = time.monotonic()

    try:
        # ── Batch mode: --complex-dir ─────────────────────────────────────
        if complex_dir:
            from bind_tools.common.batch import glob_input_dir

            complexes = glob_input_dir(complex_dir, (".pdb", ".cif"), "complex directory")
            art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "plip_artifacts"

            if dry_run:
                console.print(f"[yellow]Dry run: would profile {len(complexes)} complexes[/yellow]")
                raise typer.Exit(0)

            if not quiet:
                console.print(f"[bold]Profiling {len(complexes)} complexes...[/bold]")

            all_summaries: list[dict] = []
            failed_items: list[dict[str, str]] = []
            for complex_path in complexes:
                try:
                    spec_i = PlipProfileSpec(
                        complexPath=str(complex_path),
                        bindingSite=binding_site,
                        model=model,
                        outputs=PlipOutputs(txt=txt, xml=xml, pymol=pymol, pics=pics),
                        structureHandling=PlipStructureHandling(noHydro=nohydro),
                    )
                    summary_i = run_profile(spec_i, art_dir / complex_path.stem)
                    summary_i["source_file"] = str(complex_path)
                    summary_i["total_interactions"] = sum(
                        summary_i.get("interactionCounts", {}).values()
                    )
                    all_summaries.append(summary_i)
                except Exception as exc:
                    failed_items.append({"id": complex_path.name, "error": str(exc)})
                    if not quiet:
                        console.print(f"  [red]{complex_path.name}: {exc}[/red]")

            # Sort by total interactions descending
            all_summaries.sort(key=lambda s: s.get("total_interactions", 0), reverse=True)

            # Apply top-N
            total_count = len(all_summaries)
            if top_n is not None:
                effective_top_n = min(top_n, 100)
                all_summaries = all_summaries[:effective_top_n]

            result.summary = {
                "mode": "batch",
                "totalComplexes": len(complexes),
                "profiled": total_count,
                "failed": len(failed_items),
                "complexes": all_summaries,
            }
            result.status = "succeeded"
            result.artifacts = {"directory": str(art_dir)}

            # Write manifest
            from bind_tools.common.manifest import write_manifest
            manifest_path = Path(complex_dir) / "MANIFEST_plip.md"
            interaction_counts_cols = ["H-bonds", "Hydrophobic", "Salt Bridges", "Pi-Stacking"]
            write_manifest(
                path=manifest_path,
                title="bind-plip profile — Interaction Profiling Results",
                columns=["Rank", "Complex", "Total Interactions", "Residues", "Sites"],
                rows=[
                    [
                        str(i + 1),
                        Path(s.get("source_file", "")).name,
                        str(s.get("total_interactions", 0)),
                        str(len(s.get("interactingResidues", []))),
                        str(len(s.get("bindingSites", []))),
                    ]
                    for i, s in enumerate(all_summaries)
                ],
                metadata={
                    "Total complexes": str(len(complexes)),
                    "Profiled": str(total_count),
                    "Failed": str(len(failed_items)),
                    "Top N shown": str(len(all_summaries)),
                },
                failed_items=failed_items if failed_items else None,
            )
            result.artifacts["manifestPath"] = str(manifest_path)

            if not quiet:
                console.print(
                    f"[green]Batch PLIP complete: {total_count} profiled, "
                    f"{len(failed_items)} failed[/green]"
                )

        else:
            # ── Single complex mode ───────────────────────────────────────
            # ── Load from request file or direct flags ────────────────────
            if request or stdin_json:
                req = load_request(request, stdin_json, PlipProfileRequest)
                spec = req.spec
                result.metadata = req.metadata
            else:
                if not complex and not pdb_id:
                    console.print("[red]Provide --complex, --complex-dir, --pdb-id, or --request[/red]")
                    raise typer.Exit(2)

                spec = PlipProfileSpec(
                    complexPath=complex,
                    pdbId=pdb_id,
                    bindingSite=binding_site,
                    model=model,
                    outputs=PlipOutputs(
                        txt=txt,
                        xml=xml,
                        pymol=pymol,
                        pics=pics,
                    ),
                    structureHandling=PlipStructureHandling(
                        noHydro=nohydro,
                    ),
                )

            # Record resolved inputs
            result.inputs_resolved = {
                "complexPath": spec.complex_path,
                "pdbId": spec.pdb_id,
                "bindingSite": spec.binding_site,
            }
            result.parameters_resolved = {
                "model": spec.model,
                "outputs": spec.outputs.model_dump(),
                "structureHandling": spec.structure_handling.model_dump(by_alias=True),
            }

            if verbose and not quiet:
                console.print(f"[dim]Complex: {spec.complex_path or spec.pdb_id}[/dim]")
                console.print(f"[dim]Binding site: {spec.binding_site or 'all'}[/dim]")
                console.print(f"[dim]Model: {spec.model}[/dim]")

            if dry_run:
                console.print(
                    f"[yellow]Dry run: would profile "
                    f"'{spec.complex_path or spec.pdb_id}' "
                    f"(site={spec.binding_site or 'all'}, model={spec.model})[/yellow]"
                )
                raise typer.Exit(0)

            # ── Resolve artifacts directory ──────────────────────────────
            art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "plip_artifacts"

            # ── Run PLIP profiling ───────────────────────────────────────
            summary = run_profile(spec, art_dir)
            result.summary = summary
            result.status = "succeeded"
            result.artifacts = {"directory": str(art_dir)}

            if not quiet:
                n_sites = len(summary.get("bindingSites", []))
                n_interactions = sum(summary.get("interactionCounts", {}).values())
                n_residues = len(summary.get("interactingResidues", []))
                console.print(
                    f"[green]PLIP profiling complete: "
                    f"{n_sites} binding site(s), "
                    f"{n_interactions} interaction(s), "
                    f"{n_residues} interacting residue(s)[/green]"
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


@app.command()
def doctor() -> None:
    """Check environment for bind-plip dependencies."""
    console.print("[bold]bind-plip doctor[/bold]")

    # Check PLIP library
    if check_installed():
        console.print("  [green]OK[/green] plip Python library is installed")
    else:
        console.print("  [red]MISSING[/red] plip Python library (pip install plip)")

    # Check Open Babel
    if check_openbabel_installed():
        console.print("  [green]OK[/green] Open Babel (obabel) is installed")
    else:
        console.print(
            "  [red]MISSING[/red] Open Babel (obabel) not found on PATH "
            "(install via: conda install -c conda-forge openbabel)"
        )

    # Check PLIP CLI
    if shutil.which("plip"):
        console.print("  [green]OK[/green] plip CLI is on PATH")
    else:
        console.print(
            "  [yellow]WARN[/yellow] plip CLI not found on PATH "
            "(needed only for --txt/--xml/--pymol/--pics output)"
        )


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema(["PlipProfileRequest", "PlipProfileResult"])


if __name__ == "__main__":
    app()
