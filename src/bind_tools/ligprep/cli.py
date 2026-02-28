"""bind-ligprep CLI: ligand preparation for docking."""

from __future__ import annotations

import re
import time
from pathlib import Path

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError

from .models import (
    LigPrepInput,
    LigPrepOptions,
    LigPrepRequest,
    LigPrepResult,
    LigPrepSpec,
)
from .runner import (
    check_meeko_installed,
    check_obabel_installed,
    check_rdkit_installed,
    run_prepare,
)

app = typer.Typer(name="bind-ligprep", help="Ligand preparation for docking.")

# Characters that suggest a SMILES string (beyond simple alphanumerics)
_SMILES_CHARS = re.compile(r"[=#@\[\]\\/().+\-]")


def _parse_ligand_flag(value: str) -> LigPrepInput:
    """Detect the type of --ligand value and return a LigPrepInput."""
    p = Path(value)
    if p.is_file():
        suffix = p.suffix.lower()
        if suffix == ".mol2":
            return LigPrepInput(mol2Path=str(p.resolve()))
        # Default to SDF for any file
        return LigPrepInput(sdfPath=str(p.resolve()))

    if value.upper().startswith("CID:"):
        cid = int(value.split(":", 1)[1])
        return LigPrepInput(pubchemCid=cid)

    if _SMILES_CHARS.search(value):
        return LigPrepInput(smiles=value)

    # Treat as compound name
    return LigPrepInput(name=value)


@app.command()
def prepare(
    # ── Request loading ──────────────────────────────────────────────────
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    # ── Input ─────────────────────────────────────────────────────────────
    ligand: list[str] = typer.Option(
        [], "--ligand", help="SDF/MOL2 path, SMILES, compound name, or CID:12345 (repeatable)"
    ),
    manifest: str = typer.Option(None, "--manifest", help="CSV or JSONL manifest file"),
    # ── Options ───────────────────────────────────────────────────────────
    ph: float = typer.Option(7.4, "--ph", help="Target pH for protonation"),
    enumerate_tautomers: bool = typer.Option(
        False, "--enumerate-tautomers/--no-enumerate-tautomers", help="Enumerate tautomers"
    ),
    enumerate_protomers: bool = typer.Option(
        False, "--enumerate-protomers/--no-enumerate-protomers", help="Enumerate protomers"
    ),
    max_variants: int = typer.Option(4, "--max-variants", help="Max tautomer/protomer variants"),
    num_conformers: int = typer.Option(1, "--num-conformers", help="Number of 3D conformers"),
    charge_model: str = typer.Option("gasteiger", "--charge-model", help="Charge model (gasteiger, mmff94, none)"),
    output_formats: str = typer.Option("sdf", "--output-formats", help="Comma-separated output formats (sdf, pdbqt, mol2)"),
    engine: str = typer.Option("auto", "--engine", help="Engine: auto, rdkit, obabel, meeko"),
    # ── Output envelope ──────────────────────────────────────────────────
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result envelope"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    artifacts_dir: str = typer.Option(None, "--artifacts-dir", help="Directory for output artifacts"),
    # ── Behavioural flags ────────────────────────────────────────────────
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan, don't execute"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Prepare ligand(s) for docking (protonate, charge, conformers, format conversion)."""
    result = LigPrepResult()
    start = time.monotonic()

    try:
        # ── Load from request file or build spec from flags ──────────────
        if request or stdin_json:
            req = load_request(request, stdin_json, LigPrepRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not ligand and not manifest:
                console.print("[red]Provide --ligand, --manifest, or --request[/red]")
                raise typer.Exit(2)

            # Parse --ligand values
            ligands = [_parse_ligand_flag(v) for v in ligand]

            fmt_list = [f.strip().lower() for f in output_formats.split(",") if f.strip()]

            spec = LigPrepSpec(
                ligands=ligands,
                manifestPath=manifest,
                options=LigPrepOptions(
                    ph=ph,
                    enumerateTautomers=enumerate_tautomers,
                    enumerateProtomers=enumerate_protomers,
                    maxVariants=max_variants,
                    numConformers=num_conformers,
                    chargeModel=charge_model,
                    outputFormats=fmt_list,
                    engine=engine,
                ),
            )

        # Record resolved inputs
        ligand_descriptions = []
        for lig in spec.ligands:
            desc = lig.smiles or lig.name or lig.sdf_path or lig.mol2_path
            if lig.pubchem_cid is not None:
                desc = f"CID:{lig.pubchem_cid}"
            ligand_descriptions.append(desc or "unknown")

        result.inputs_resolved = {
            "ligands": ligand_descriptions,
            "manifestPath": spec.manifest_path,
        }
        result.parameters_resolved = {
            "options": spec.options.model_dump(by_alias=True),
        }

        if verbose and not quiet:
            console.print(f"[dim]Ligands: {ligand_descriptions}[/dim]")
            console.print(f"[dim]pH: {spec.options.ph}[/dim]")
            console.print(f"[dim]Engine: {spec.options.engine.value}[/dim]")
            console.print(f"[dim]Output formats: {spec.options.output_formats}[/dim]")

        if dry_run:
            total = len(spec.ligands)
            if spec.manifest_path:
                console.print(
                    f"[yellow]Dry run: would prepare {total} ligand(s) "
                    f"+ manifest '{spec.manifest_path}' "
                    f"(pH={spec.options.ph}, engine={spec.options.engine.value})[/yellow]"
                )
            else:
                console.print(
                    f"[yellow]Dry run: would prepare {total} ligand(s) "
                    f"(pH={spec.options.ph}, engine={spec.options.engine.value})[/yellow]"
                )
            console.print(
                f"[yellow]  Output formats: {', '.join(spec.options.output_formats)}[/yellow]"
            )
            console.print(
                f"[yellow]  Charge model: {spec.options.charge_model}[/yellow]"
            )
            console.print(
                f"[yellow]  Conformers: {spec.options.num_conformers}[/yellow]"
            )
            for desc in ligand_descriptions:
                console.print(f"[yellow]  - {desc}[/yellow]")
            raise typer.Exit(0)

        # ── Resolve artifacts directory ──────────────────────────────────
        art_dir = Path(artifacts_dir) if artifacts_dir else Path.cwd() / "ligprep_artifacts"

        # ── Run preparation pipeline ─────────────────────────────────────
        summary = run_prepare(spec, art_dir)
        result.summary = summary
        result.artifacts = {
            "directory": str(art_dir),
        }

        succeeded = summary.get("succeeded", 0)
        failed = summary.get("failed", 0)
        total = summary.get("total", 0)

        if failed > 0 and succeeded > 0:
            result.status = "partial"
        elif failed > 0:
            result.status = "failed"
        else:
            result.status = "succeeded"

        if not quiet:
            console.print(
                f"[green]Ligand preparation complete: "
                f"{succeeded}/{total} succeeded[/green]"
            )
            if failed > 0:
                console.print(f"[yellow]{failed} ligand(s) failed[/yellow]")

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
    """Check environment for bind-ligprep dependencies."""
    console.print("[bold]bind-ligprep doctor[/bold]")

    # RDKit (primary engine)
    if check_rdkit_installed():
        console.print("  [green]OK[/green] rdkit is installed")
    else:
        console.print(
            "  [red]MISSING[/red] rdkit (pip install rdkit) — required"
        )

    # Open Babel (format conversion)
    if check_obabel_installed():
        console.print("  [green]OK[/green] obabel is installed")
    else:
        console.print(
            "  [yellow]WARN[/yellow] obabel not installed "
            "— needed for MOL2 output and PDBQT fallback"
        )

    # Meeko (PDBQT)
    if check_meeko_installed():
        console.print("  [green]OK[/green] meeko is installed")
    else:
        console.print(
            "  [yellow]WARN[/yellow] meeko not installed "
            "(pip install meeko) — needed for PDBQT output"
        )


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema(["LigPrepRequest", "LigPrepResult"])


def main() -> None:
    app()


if __name__ == "__main__":
    app()
