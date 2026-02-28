"""bind-protprep CLI: protein structure preparation."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError

from .models import (
    ProtPrepOptions,
    ProtPrepRequest,
    ProtPrepResult,
    ProtPrepSpec,
    ProtPrepSteps,
)
from .runner import (
    check_openmm_installed,
    check_pdb2pqr_installed,
    check_pdbfixer_installed,
    run_prepare,
)

app = typer.Typer(name="bind-protprep", help="Protein structure preparation for docking.")


@app.command()
def prepare(
    # ── Request loading ──────────────────────────────────────────────────
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    # ── Direct spec flags ────────────────────────────────────────────────
    input: str = typer.Option(None, "--input", help="Path to PDB/CIF file"),
    pdb_id: str = typer.Option(None, "--pdb-id", help="4-letter PDB ID to fetch from RCSB"),
    # ── Step toggles ─────────────────────────────────────────────────────
    add_hydrogens: bool = typer.Option(True, "--add-hydrogens/--no-add-hydrogens", help="Add missing hydrogens"),
    fill_residues: bool = typer.Option(True, "--fill-residues/--no-fill-residues", help="Fill missing residues/loops"),
    fill_atoms: bool = typer.Option(True, "--fill-atoms/--no-fill-atoms", help="Fill missing heavy atoms"),
    remove_heterogens: bool = typer.Option(True, "--remove-heterogens/--no-remove-heterogens", help="Remove heterogens"),
    remove_water: bool = typer.Option(True, "--remove-water/--no-remove-water", help="Remove water molecules"),
    replace_nonstandard: bool = typer.Option(True, "--replace-nonstandard/--no-replace-nonstandard", help="Replace non-standard residues"),
    assign_protonation: bool = typer.Option(True, "--assign-protonation/--no-assign-protonation", help="Assign protonation states via pdb2pqr"),
    energy_minimize: bool = typer.Option(True, "--energy-minimize/--no-energy-minimize", help="Energy minimize via OpenMM"),
    # ── Fine-grained options ─────────────────────────────────────────────
    ph: float = typer.Option(7.4, "--ph", help="Target pH for protonation"),
    chain: list[str] = typer.Option([], "--chain", help="Chain(s) to keep (repeatable, empty=all)"),
    keep_water_within: float = typer.Option(None, "--keep-water-within", help="Keep waters within N angstroms of heterogens"),
    force_field: str = typer.Option("amber14-all.xml", "--force-field", help="OpenMM force field XML"),
    max_minimize_iters: int = typer.Option(500, "--max-minimize-iters", help="Max minimization iterations"),
    # ── Output envelope ──────────────────────────────────────────────────
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output artifacts"),
    # ── Behavioural flags ────────────────────────────────────────────────
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan, don't execute"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Prepare a protein structure for docking (fix, protonate, minimize)."""
    result = ProtPrepResult()
    start = time.monotonic()

    try:
        # ── Load from request file or direct flags ───────────────────────
        if request or stdin_json:
            req = load_request(request, stdin_json, ProtPrepRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not input and not pdb_id:
                console.print("[red]Provide --input, --pdb-id, or --request[/red]")
                raise typer.Exit(2)

            spec = ProtPrepSpec(
                inputPath=input,
                pdbId=pdb_id,
                steps=ProtPrepSteps(
                    addHydrogens=add_hydrogens,
                    fillMissingResidues=fill_residues,
                    fillMissingAtoms=fill_atoms,
                    removeHeterogens=remove_heterogens,
                    removeWater=remove_water,
                    replaceNonstandard=replace_nonstandard,
                    assignProtonation=assign_protonation,
                    energyMinimize=energy_minimize,
                ),
                options=ProtPrepOptions(
                    ph=ph,
                    chains=chain,
                    keepWaterWithin=keep_water_within,
                    forceField=force_field,
                    maxMinimizeIterations=max_minimize_iters,
                ),
            )

        # Record resolved inputs
        result.inputs_resolved = {
            "inputPath": spec.input_path,
            "pdbId": spec.pdb_id,
        }
        result.parameters_resolved = {
            "steps": spec.steps.model_dump(by_alias=True),
            "options": spec.options.model_dump(by_alias=True),
        }

        if verbose and not quiet:
            console.print(f"[dim]Input: {spec.input_path or spec.pdb_id}[/dim]")
            console.print(f"[dim]pH: {spec.options.ph}[/dim]")
            console.print(f"[dim]Chains: {spec.options.chains or 'all'}[/dim]")

        if dry_run:
            enabled = [
                name for name, enabled in spec.steps.model_dump().items() if enabled
            ]
            disabled = [
                name for name, enabled in spec.steps.model_dump().items() if not enabled
            ]
            console.print(
                f"[yellow]Dry run: would prepare "
                f"'{spec.input_path or spec.pdb_id}' "
                f"(pH={spec.options.ph}, chains={spec.options.chains or 'all'})[/yellow]"
            )
            console.print(f"[yellow]  Enabled steps: {', '.join(enabled)}[/yellow]")
            if disabled:
                console.print(f"[yellow]  Disabled steps: {', '.join(disabled)}[/yellow]")
            raise typer.Exit(0)

        # ── Resolve artifacts directory ──────────────────────────────────
        art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "protprep_artifacts"

        # ── Run preparation pipeline ─────────────────────────────────────
        summary = run_prepare(spec, art_dir)
        result.summary = summary
        result.status = "succeeded"
        result.artifacts = {
            "directory": str(art_dir),
            "output_file": summary.get("outputPath", ""),
        }

        if not quiet:
            n_h = summary.get("hydrogensAdded", 0)
            n_res = summary.get("residuesFilled", 0)
            out_path = summary.get("outputPath", "")
            console.print(
                f"[green]Protein preparation complete: "
                f"{n_h} hydrogen(s) added, "
                f"{n_res} residue segment(s) filled[/green]"
            )
            console.print(f"[green]Output: {out_path}[/green]")

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
    """Check environment for bind-protprep dependencies."""
    console.print("[bold]bind-protprep doctor[/bold]")

    # PDBFixer (required)
    if check_pdbfixer_installed():
        console.print("  [green]OK[/green] pdbfixer is installed")
    else:
        console.print(
            "  [red]MISSING[/red] pdbfixer (pip install pdbfixer) — required"
        )

    # OpenMM (for energy minimization)
    if check_openmm_installed():
        console.print("  [green]OK[/green] OpenMM is installed")
    else:
        console.print(
            "  [yellow]WARN[/yellow] OpenMM not installed "
            "(pip install openmm) — needed for energy minimization"
        )

    # pdb2pqr (for protonation states)
    if check_pdb2pqr_installed():
        console.print("  [green]OK[/green] pdb2pqr is installed")
    else:
        console.print(
            "  [yellow]WARN[/yellow] pdb2pqr not installed "
            "(pip install pdb2pqr) — needed for protonation state assignment"
        )


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema(["ProtPrepRequest", "ProtPrepResult"])


def main() -> None:
    app()


if __name__ == "__main__":
    app()
