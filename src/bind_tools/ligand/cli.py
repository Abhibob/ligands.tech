"""CLI interface for ligand resolution.

Usage:
  bind-ligand resolve --name erlotinib --json-out result.json
  bind-ligand resolve --smiles "C#Cc1cccc(Nc2ncnc3cc(OCCOC)c(OCCOC)cc23)c1" --json-out result.json
  bind-ligand resolve --cid 176870 --json-out result.json
  bind-ligand resolve --request request.yaml --json-out result.json
"""

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from typing_extensions import Annotated

from .models import LigandSearchInput
from .resolver import resolve_ligand

app = typer.Typer(
    name="bind-ligand",
    help="Ligand resolution CLI - resolve ligand names to SMILES and 3D structures",
    add_completion=False,
)

console = Console()


@app.command()
def resolve(
    # Input methods (mutually exclusive)
    name: Annotated[
        Optional[str], typer.Option("--name", help="Ligand/drug name (e.g., 'erlotinib')")
    ] = None,
    smiles: Annotated[
        Optional[str], typer.Option("--smiles", help="SMILES string")
    ] = None,
    cid: Annotated[
        Optional[int], typer.Option("--cid", help="PubChem CID (e.g., 176870)")
    ] = None,
    request: Annotated[
        Optional[Path],
        typer.Option("--request", help="Request file (JSON or YAML)", exists=True),
    ] = None,
    stdin_json: Annotated[
        bool, typer.Option("--stdin-json", help="Read request from stdin as JSON")
    ] = False,
    # Parameters
    generate_3d: Annotated[
        bool, typer.Option("--generate-3d/--no-3d", help="Generate 3D coordinates")
    ] = True,
    # Output
    json_out: Annotated[
        Optional[Path], typer.Option("--json-out", help="Output JSON file")
    ] = None,
    yaml_out: Annotated[
        Optional[Path], typer.Option("--yaml-out", help="Output YAML file")
    ] = None,
    # Workspace
    artifacts_dir: Annotated[
        str, typer.Option("--artifacts-dir", help="Directory for downloaded files")
    ] = "./workspace",
    workspace_dir: Annotated[
        Optional[str], typer.Option("--workspace-dir", help="Alias for --artifacts-dir")
    ] = None,
    # Metadata
    run_id: Annotated[
        Optional[str], typer.Option("--run-id", help="Run identifier for tracking")
    ] = None,
    # Flags
    verbose: Annotated[bool, typer.Option("--verbose", "-v", help="Verbose output")] = False,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress output")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Validate inputs only")] = False,
):
    """Resolve a ligand name/SMILES to PubChem data, SMILES, and 3D SDF files."""

    workspace = workspace_dir or artifacts_dir

    try:
        # Parse input
        if stdin_json:
            stdin_data = sys.stdin.read()
            try:
                request_data = json.loads(stdin_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]✗ Invalid JSON from stdin: {e}[/red]", file=sys.stderr)
                raise typer.Exit(code=2)

            search_input = LigandSearchInput(**request_data)

        elif request:
            request_text = request.read_text()
            try:
                if request.suffix.lower() in [".yaml", ".yml"]:
                    request_data = yaml.safe_load(request_text)
                else:
                    request_data = json.loads(request_text)
            except Exception as e:
                console.print(
                    f"[red]✗ Failed to parse request file: {e}[/red]", file=sys.stderr
                )
                raise typer.Exit(code=2)

            search_input = LigandSearchInput(**request_data)

        else:
            # Direct arguments
            if cid:
                query = f"CID:{cid}"
            else:
                query = name or smiles

            if not query:
                console.print(
                    "[red]✗ Must provide --name, --smiles, --cid, --request, or --stdin-json[/red]",
                    file=sys.stderr,
                )
                raise typer.Exit(code=2)

            search_input = LigandSearchInput(
                query=query,
                generate_3d=generate_3d,
                workspace_dir=workspace,
            )

        if dry_run:
            console.print("[yellow]Dry run - inputs validated:[/yellow]")
            console.print(search_input.model_dump_json(indent=2))
            raise typer.Exit(code=0)

        # Execute resolution
        start_time = datetime.utcnow()

        if not quiet:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    f"Resolving ligand '{search_input.query}'...", total=None
                )
                result = asyncio.run(resolve_ligand(search_input))
                progress.update(task, completed=True)
        else:
            result = asyncio.run(resolve_ligand(search_input))

        end_time = datetime.utcnow()
        runtime = (end_time - start_time).total_seconds()

        # Build binding.dev/v1 envelope
        request_id = run_id or f"resolve-ligand-{uuid.uuid4()}"

        envelope = {
            "apiVersion": "binding.dev/v1",
            "kind": "ResolveLigandResult",
            "metadata": {
                "requestId": request_id,
                "createdAt": start_time.isoformat() + "Z",
            },
            "tool": "ligand-resolver",
            "wrapperVersion": "0.1.0",
            "status": "succeeded",
            "inputsResolved": {
                "query": result.query,
            },
            "parametersResolved": {
                "generate_3d": generate_3d,
            },
            "summary": {
                "name": result.name,
                "pubchem_cid": result.pubchem_cid,
                "chembl_id": result.chembl_id,
                "smiles": result.smiles,
                "isomeric_smiles": result.isomeric_smiles,
                "inchi_key": result.inchi_key,
                "iupac_name": result.iupac_name,
                "properties": result.properties.model_dump() if result.properties else None,
                "max_clinical_phase": result.max_clinical_phase,
            },
            "artifacts": {
                "sdf_2d": result.sdf_2d_path,
                "sdf_3d": result.sdf_3d_path,
            },
            "warnings": [],
            "errors": [],
            "provenance": {
                "apis_used": ["PubChem PUG-REST"],
                "data_sources": ["PubChem"],
            },
            "runtimeSeconds": runtime,
        }

        # Add warnings
        if not result.sdf_3d_path and generate_3d:
            envelope["warnings"].append(
                "3D structure not available from PubChem; RDKit generation may have failed"
            )

        # Write output files
        if json_out:
            json_out.write_text(json.dumps(envelope, indent=2))
            if not quiet:
                console.print(f"[green]✓ Wrote JSON output: {json_out}[/green]")

        if yaml_out:
            yaml_out.write_text(yaml.dump(envelope, default_flow_style=False))
            if not quiet:
                console.print(f"[green]✓ Wrote YAML output: {yaml_out}[/green]")

        # Console output
        if verbose and not quiet:
            console.print(f"\n[bold]Ligand Resolution Results:[/bold]")
            console.print(f"  Name: [cyan]{result.name or 'N/A'}[/cyan]")
            if result.pubchem_cid:
                console.print(f"  PubChem CID: [cyan]{result.pubchem_cid}[/cyan]")
            if result.chembl_id:
                console.print(f"  ChEMBL ID: {result.chembl_id}")
            console.print(f"  SMILES: {result.smiles or 'N/A'}")
            if result.inchi_key:
                console.print(f"  InChI Key: {result.inchi_key}")

            if result.properties:
                console.print(f"\n  Molecular Properties:")
                if result.properties.molecular_weight:
                    console.print(f"    MW: {result.properties.molecular_weight:.2f} Da")
                if result.properties.molecular_formula:
                    console.print(f"    Formula: {result.properties.molecular_formula}")
                if result.properties.logp is not None:
                    console.print(f"    LogP: {result.properties.logp:.2f}")
                if result.properties.h_bond_donors is not None:
                    console.print(
                        f"    H-bond donors: {result.properties.h_bond_donors}"
                    )
                if result.properties.h_bond_acceptors is not None:
                    console.print(
                        f"    H-bond acceptors: {result.properties.h_bond_acceptors}"
                    )

            console.print(f"\n  Files:")
            if result.sdf_2d_path:
                console.print(f"    2D SDF: {result.sdf_2d_path}")
            if result.sdf_3d_path:
                console.print(f"    3D SDF: {result.sdf_3d_path}")

            console.print(f"\n  Runtime: {runtime:.2f}s")

        elif not quiet:
            console.print(
                f"[green]✓ Resolved {result.name or result.query} "
                f"(CID: {result.pubchem_cid or 'N/A'})[/green]"
            )

        sys.exit(0)

    except ValueError as e:
        envelope = _error_envelope(str(e), "failed", 2, run_id)
        if json_out:
            json_out.write_text(json.dumps(envelope, indent=2))
        console.print(f"[red]✗ Validation error: {e}[/red]", file=sys.stderr)
        raise typer.Exit(code=2)

    except FileNotFoundError as e:
        console.print(f"[red]✗ Input file not found: {e}[/red]", file=sys.stderr)
        raise typer.Exit(code=3)

    except Exception as e:
        envelope = _error_envelope(str(e), "failed", 1, run_id)
        if json_out:
            json_out.write_text(json.dumps(envelope, indent=2))
        console.print(f"[red]✗ Error: {e}[/red]", file=sys.stderr)
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


def _error_envelope(error_msg: str, status: str, exit_code: int, run_id: Optional[str] = None):
    """Build error envelope."""
    request_id = run_id or f"resolve-ligand-error-{uuid.uuid4()}"
    return {
        "apiVersion": "binding.dev/v1",
        "kind": "ResolveLigandResult",
        "metadata": {
            "requestId": request_id,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        },
        "tool": "ligand-resolver",
        "wrapperVersion": "0.1.0",
        "status": status,
        "errors": [error_msg],
        "exitCode": exit_code,
    }


def main():
    """Entry point for bind-ligand CLI."""
    app()


if __name__ == "__main__":
    main()
