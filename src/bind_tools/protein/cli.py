"""CLI interface for protein resolution.

Usage:
  bind-protein resolve --name EGFR --json-out result.json
  bind-protein resolve --uniprot P00533 --organism human --json-out result.json
  bind-protein resolve --request request.yaml --json-out result.json
  cat request.json | bind-protein resolve --stdin-json --json-out result.json
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

from .models import ProteinSearchInput
from .resolver import resolve_protein

app = typer.Typer(
    name="bind-protein",
    help="Protein resolution CLI - resolve protein names to structures and sequences",
    add_completion=False,
)

console = Console()


@app.command()
def resolve(
    # Input methods (mutually exclusive)
    name: Annotated[
        Optional[str], typer.Option("--name", help="Protein name or gene symbol")
    ] = None,
    uniprot: Annotated[
        Optional[str], typer.Option("--uniprot", help="UniProt accession (e.g., P00533)")
    ] = None,
    request: Annotated[
        Optional[Path],
        typer.Option("--request", help="Request file (JSON or YAML)", exists=True),
    ] = None,
    stdin_json: Annotated[
        bool, typer.Option("--stdin-json", help="Read request from stdin as JSON")
    ] = False,
    # Parameters
    organism: Annotated[
        str, typer.Option("--organism", help="Target organism")
    ] = "Homo sapiens",
    max_structures: Annotated[
        int, typer.Option("--max-structures", help="Maximum PDB structures to return")
    ] = 5,
    download_best: Annotated[
        bool, typer.Option("--download-best/--no-download", help="Download best structure files")
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
    """Resolve a protein name to UniProt accession, FASTA sequence, and PDB structures."""

    # Use workspace_dir if provided, otherwise artifacts_dir
    workspace = workspace_dir or artifacts_dir

    try:
        # Parse input
        if stdin_json:
            # Read from stdin
            stdin_data = sys.stdin.read()
            try:
                request_data = json.loads(stdin_data)
            except json.JSONDecodeError as e:
                console.print(f"[red]✗ Invalid JSON from stdin: {e}[/red]", file=sys.stderr)
                raise typer.Exit(code=2)

            search_input = ProteinSearchInput(**request_data)

        elif request:
            # Read from file
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

            search_input = ProteinSearchInput(**request_data)

        else:
            # Direct arguments
            query = name or uniprot
            if not query:
                console.print(
                    "[red]✗ Must provide --name, --uniprot, --request, or --stdin-json[/red]",
                    file=sys.stderr,
                )
                raise typer.Exit(code=2)

            search_input = ProteinSearchInput(
                query=query,
                organism=organism,
                max_structures=max_structures,
                download_best=download_best,
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
                    f"Resolving protein '{search_input.query}'...", total=None
                )
                result = asyncio.run(resolve_protein(search_input))
                progress.update(task, completed=True)
        else:
            result = asyncio.run(resolve_protein(search_input))

        end_time = datetime.utcnow()
        runtime = (end_time - start_time).total_seconds()

        # Build binding.dev/v1 envelope
        request_id = run_id or f"resolve-{uuid.uuid4()}"

        envelope = {
            "apiVersion": "binding.dev/v1",
            "kind": "ResolveProteinResult",
            "metadata": {
                "requestId": request_id,
                "createdAt": start_time.isoformat() + "Z",
            },
            "tool": "protein-resolver",
            "wrapperVersion": "0.1.0",
            "status": "succeeded",
            "inputsResolved": {
                "query": result.query,
                "organism": result.organism,
            },
            "parametersResolved": {
                "max_structures": max_structures,
                "download_best": download_best,
            },
            "summary": {
                "uniprot_id": result.uniprot_id,
                "gene_name": result.gene_name,
                "protein_name": result.protein_name,
                "organism": result.organism,
                "sequence_length": result.sequence_length,
                "structures_found": len(result.structures),
                "best_structure": (
                    {
                        "pdb_id": result.best_structure.pdb_id,
                        "resolution": result.best_structure.resolution,
                        "method": result.best_structure.method,
                        "has_ligand": result.best_structure.has_ligand,
                        "ligand_ids": result.best_structure.ligand_ids,
                    }
                    if result.best_structure
                    else None
                ),
                "binding_sites_found": len(result.binding_sites),
            },
            "artifacts": {
                "fasta": result.fasta_path,
                "pdb": result.best_structure.pdb_path if result.best_structure else None,
                "cif": result.best_structure.cif_path if result.best_structure else None,
            },
            "warnings": [],
            "errors": [],
            "provenance": {
                "apis_used": ["UniProt REST", "RCSB PDB Search", "RCSB PDB Data"],
                "data_sources": ["UniProt", "RCSB PDB"],
            },
            "runtimeSeconds": runtime,
        }

        # Add warnings if applicable
        if not result.structures:
            envelope["warnings"].append("No PDB structures found for this protein")
        if not result.binding_sites:
            envelope["warnings"].append("No annotated binding sites found")
        if result.best_structure and not result.best_structure.pdb_path:
            envelope["warnings"].append("Structure download failed")

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
            console.print(f"\n[bold]Protein Resolution Results:[/bold]")
            console.print(f"  UniProt ID: [cyan]{result.uniprot_id}[/cyan]")
            console.print(f"  Gene: [cyan]{result.gene_name}[/cyan]")
            console.print(f"  Protein: {result.protein_name}")
            console.print(f"  Organism: {result.organism}")
            console.print(f"  Sequence: {result.sequence_length} amino acids")
            console.print(f"  FASTA: {result.fasta_path}")
            console.print(f"\n  Structures found: {len(result.structures)}")
            if result.best_structure:
                console.print(f"  Best structure: [cyan]{result.best_structure.pdb_id}[/cyan]")
                console.print(f"    Resolution: {result.best_structure.resolution}Å")
                console.print(f"    Method: {result.best_structure.method}")
                console.print(
                    f"    Ligand-bound: {'Yes' if result.best_structure.has_ligand else 'No'}"
                )
                if result.best_structure.pdb_path:
                    console.print(f"    PDB file: {result.best_structure.pdb_path}")
            console.print(f"\n  Binding sites: {len(result.binding_sites)}")
            console.print(f"\n  Runtime: {runtime:.2f}s")

        elif not quiet:
            console.print(
                f"[green]✓ Resolved {result.gene_name} ({result.uniprot_id})[/green]"
            )

        sys.exit(0)

    except ValueError as e:
        # Validation error (protein not found, invalid input)
        envelope = _error_envelope(str(e), "failed", 2, run_id)
        if json_out:
            json_out.write_text(json.dumps(envelope, indent=2))
        console.print(f"[red]✗ Validation error: {e}[/red]", file=sys.stderr)
        raise typer.Exit(code=2)

    except FileNotFoundError as e:
        # Input file missing
        console.print(f"[red]✗ Input file not found: {e}[/red]", file=sys.stderr)
        raise typer.Exit(code=3)

    except Exception as e:
        # Unexpected error
        envelope = _error_envelope(str(e), "failed", 1, run_id)
        if json_out:
            json_out.write_text(json.dumps(envelope, indent=2))
        console.print(f"[red]✗ Error: {e}[/red]", file=sys.stderr)
        if verbose:
            console.print_exception()
        raise typer.Exit(code=1)


def _error_envelope(error_msg: str, status: str, exit_code: int, run_id: Optional[str] = None):
    """Build error envelope."""
    request_id = run_id or f"resolve-error-{uuid.uuid4()}"
    return {
        "apiVersion": "binding.dev/v1",
        "kind": "ResolveProteinResult",
        "metadata": {
            "requestId": request_id,
            "createdAt": datetime.utcnow().isoformat() + "Z",
        },
        "tool": "protein-resolver",
        "wrapperVersion": "0.1.0",
        "status": status,
        "errors": [error_msg],
        "exitCode": exit_code,
    }


def main():
    """Entry point for bind-protein CLI."""
    app()


if __name__ == "__main__":
    main()
