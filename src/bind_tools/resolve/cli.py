"""Typer CLI for bind-resolve: resolve protein, ligand, and binder identifiers."""

from __future__ import annotations

import time

import typer
from rich.console import Console
from rich.table import Table

from bind_tools.common.cli_base import write_result
from bind_tools.common.errors import BindToolError

from .models import ResolveBindersResult, ResolveLigandResult, ResolveProteinResult
from .runner import (
    CHEMBL_BASE,
    ORGANISM_MAP,
    resolve_binders,
    resolve_ligand,
    resolve_protein,
    search_structures,
)

app = typer.Typer(
    name="resolve",
    help="Resolve protein, ligand, and binder identifiers from public databases.",
    no_args_is_help=True,
)
console = Console(stderr=True)


# ── protein ──────────────────────────────────────────────────────────────────


@app.command()
def protein(
    name: str | None = typer.Option(None, "--name", help="Gene name (e.g. EGFR, TP53, BRAF)."),
    organism: str = typer.Option("human", "--organism", help="Organism common name or NCBI taxonomy ID."),
    uniprot: str | None = typer.Option(None, "--uniprot", help="UniProt accession (skip search)."),
    download_dir: str | None = typer.Option(None, "--download-dir", help="Directory to download the best PDB structure."),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope to file."),
    yaml_out: str | None = typer.Option(None, "--yaml-out", help="Write YAML result envelope to file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs and print plan, do not execute."),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose logging output."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational output."),
) -> None:
    """Resolve a protein target to UniProt, PDB structures, and AlphaFold."""
    if dry_run:
        console.print("[bold]Dry-run:[/bold] would resolve protein with:")
        console.print(f"  name={name}, organism={organism}, uniprot={uniprot}")
        console.print(f"  download_dir={download_dir}")
        raise typer.Exit(0)

    result = ResolveProteinResult()
    result.inputs_resolved = {
        "name": name,
        "organism": organism,
        "uniprot": uniprot,
        "download_dir": download_dir,
    }

    start = time.monotonic()
    try:
        summary = resolve_protein(
            name=name,
            organism=organism,
            uniprot_id=uniprot,
            download_dir=download_dir,
        )
        result.summary = summary
        result.status = "succeeded"

        if not quiet:
            _print_protein_summary(summary, verbose)

    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        console.print(f"[red]Error:[/red] {exc}")
    finally:
        result.runtime_seconds = round(time.monotonic() - start, 3)

    write_result(result, json_out, yaml_out)


def _print_protein_summary(summary: dict, verbose: bool) -> None:
    """Pretty-print the protein resolution summary."""
    console.print(f"\n[bold green]Protein resolved:[/bold green] {summary.get('protein_name', 'N/A')}")
    console.print(f"  UniProt:  {summary.get('uniprot_accession', 'N/A')}")
    console.print(f"  Gene:     {summary.get('gene_name', 'N/A')}")
    console.print(f"  Organism: {summary.get('organism', 'N/A')}")

    structures = summary.get("best_structures", [])
    if structures:
        table = Table(title=f"Top {len(structures)} PDB Structures")
        table.add_column("PDB ID", style="cyan")
        table.add_column("Resolution", justify="right")
        table.add_column("Method")
        table.add_column("Chain")
        table.add_column("Coverage", justify="right")
        for s in structures:
            res = f"{s['resolution']:.2f}" if s.get("resolution") else "N/A"
            cov = f"{s.get('coverage', 0):.1%}" if isinstance(s.get("coverage"), (int, float)) else "N/A"
            table.add_row(
                s.get("pdb_id", ""),
                res,
                s.get("experimental_method", ""),
                s.get("chain_id", ""),
                cov,
            )
        console.print(table)
    else:
        console.print("  [yellow]No experimental structures found.[/yellow]")

    if summary.get("sequence_length"):
        console.print(f"  Sequence length: {summary['sequence_length']} aa")
    if summary.get("fasta_path"):
        console.print(f"  FASTA: {summary['fasta_path']}")

    binding_sites = summary.get("binding_sites", [])
    if binding_sites:
        bs_table = Table(title=f"Binding Sites ({len(binding_sites)})")
        bs_table.add_column("Site ID", style="cyan")
        bs_table.add_column("Ligand")
        bs_table.add_column("Residues", max_width=50)
        bs_table.add_column("Source")
        for bs in binding_sites:
            ligand_label = bs.get("ligand_id", "") or ""
            if bs.get("ligand_name"):
                ligand_label = f"{ligand_label} ({bs['ligand_name']})" if ligand_label else bs["ligand_name"]
            residues_str = ", ".join(bs.get("residues", [])[:8])
            if len(bs.get("residues", [])) > 8:
                residues_str += f" ... (+{len(bs['residues']) - 8})"
            bs_table.add_row(
                bs.get("site_id", ""),
                ligand_label,
                residues_str,
                bs.get("source", ""),
            )
        console.print(bs_table)

    dl = summary.get("downloaded_path")
    if dl:
        console.print(f"  Downloaded: {dl}")


# ── ligand ───────────────────────────────────────────────────────────────────


@app.command()
def ligand(
    name: str | None = typer.Option(None, "--name", help="Compound name (e.g. aspirin, imatinib)."),
    smiles: str | None = typer.Option(None, "--smiles", help="SMILES string for 3D generation via RDKit."),
    ccd: str | None = typer.Option(None, "--ccd", help="CCD ligand code from RCSB (e.g. ATP, HEM)."),
    pubchem_cid: int | None = typer.Option(None, "--pubchem-cid", help="PubChem compound ID."),
    download_dir: str | None = typer.Option(None, "--download-dir", help="Directory to download SDF files."),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope to file."),
    yaml_out: str | None = typer.Option(None, "--yaml-out", help="Write YAML result envelope to file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs and print plan, do not execute."),
) -> None:
    """Resolve a ligand from name, SMILES, CCD code, or PubChem CID."""
    if dry_run:
        console.print("[bold]Dry-run:[/bold] would resolve ligand with:")
        console.print(f"  name={name}, smiles={smiles}, ccd={ccd}, pubchem_cid={pubchem_cid}")
        console.print(f"  download_dir={download_dir}")
        raise typer.Exit(0)

    result = ResolveLigandResult()
    result.inputs_resolved = {
        "name": name,
        "smiles": smiles,
        "ccd": ccd,
        "pubchem_cid": pubchem_cid,
        "download_dir": download_dir,
    }

    start = time.monotonic()
    try:
        summary = resolve_ligand(
            name=name,
            smiles=smiles,
            ccd=ccd,
            pubchem_cid=pubchem_cid,
            download_dir=download_dir,
        )
        result.summary = summary
        result.status = "succeeded"

        console.print(f"\n[bold green]Ligand resolved:[/bold green] {summary.get('identifier', 'N/A')}")
        console.print(f"  Source:   {summary.get('source', 'N/A')}")
        if summary.get("name"):
            console.print(f"  Name:     {summary['name']}")
        if summary.get("smiles"):
            console.print(f"  SMILES:   {summary['smiles']}")
        if summary.get("iupac_name"):
            console.print(f"  IUPAC:    {summary['iupac_name']}")
        if summary.get("molecular_formula"):
            console.print(f"  Formula:  {summary['molecular_formula']}")
        if summary.get("molecular_weight"):
            console.print(f"  MW:       {summary['molecular_weight']}")
        if summary.get("logp") is not None:
            console.print(f"  LogP:     {summary['logp']}")
        if summary.get("tpsa") is not None:
            console.print(f"  TPSA:     {summary['tpsa']}")
        if summary.get("h_bond_donors") is not None:
            console.print(f"  HBD/HBA:  {summary['h_bond_donors']}/{summary.get('h_bond_acceptors', 'N/A')}")
        if summary.get("sdf_path"):
            console.print(f"  SDF:      {summary['sdf_path']}")

    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        console.print(f"[red]Error:[/red] {exc}")
    finally:
        result.runtime_seconds = round(time.monotonic() - start, 3)

    write_result(result, json_out, yaml_out)


# ── binders ──────────────────────────────────────────────────────────────────


@app.command()
def binders(
    gene: str | None = typer.Option(None, "--gene", help="Gene name of the target protein."),
    organism: str = typer.Option("human", "--organism", help="Organism common name."),
    uniprot: str | None = typer.Option(None, "--uniprot", help="UniProt accession of the target."),
    min_pchembl: float = typer.Option(6.0, "--min-pchembl", help="Minimum pChEMBL value for activity filter."),
    limit: int = typer.Option(20, "--limit", help="Maximum number of top compounds to return."),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope to file."),
    yaml_out: str | None = typer.Option(None, "--yaml-out", help="Write YAML result envelope to file."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs and print plan, do not execute."),
) -> None:
    """Resolve known binders and approved drugs for a protein target via ChEMBL."""
    if dry_run:
        console.print("[bold]Dry-run:[/bold] would resolve binders with:")
        console.print(f"  gene={gene}, organism={organism}, uniprot={uniprot}")
        console.print(f"  min_pchembl={min_pchembl}, limit={limit}")
        raise typer.Exit(0)

    # Map organism name to taxonomy ID for the runner
    from .runner import _resolve_organism_id

    org_id = _resolve_organism_id(organism, None)

    result = ResolveBindersResult()
    result.inputs_resolved = {
        "gene": gene,
        "organism": organism,
        "uniprot": uniprot,
        "min_pchembl": min_pchembl,
        "limit": limit,
    }

    start = time.monotonic()
    try:
        summary = resolve_binders(
            gene=gene,
            organism_id=org_id,
            uniprot_id=uniprot,
            min_pchembl=min_pchembl,
            limit=limit,
        )
        result.summary = summary
        result.status = "succeeded"

        _print_binders_summary(summary)

    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        console.print(f"[red]Error:[/red] {exc}")
    finally:
        result.runtime_seconds = round(time.monotonic() - start, 3)

    write_result(result, json_out, yaml_out)


def _print_binders_summary(summary: dict) -> None:
    """Pretty-print the binders resolution summary."""
    console.print(f"\n[bold green]Binders resolved for:[/bold green] {summary.get('target_name', 'N/A')}")
    console.print(f"  ChEMBL target: {summary.get('chembl_target_id', 'N/A')}")
    console.print(f"  UniProt:       {summary.get('uniprot_accession', 'N/A')}")

    drugs = summary.get("approved_drugs", [])
    if drugs:
        table = Table(title=f"Approved Drugs / Mechanisms ({len(drugs)})")
        table.add_column("ChEMBL ID", style="cyan")
        table.add_column("Drug Name")
        table.add_column("Mechanism")
        table.add_column("Action")
        table.add_column("Phase", justify="right")
        for d in drugs:
            table.add_row(
                d.get("molecule_chembl_id", ""),
                d.get("drug_name", ""),
                d.get("mechanism_of_action", ""),
                d.get("action_type", ""),
                str(d.get("max_phase", "")),
            )
        console.print(table)
    else:
        console.print("  [yellow]No approved drugs / mechanisms found.[/yellow]")

    compounds = summary.get("top_compounds", [])
    if compounds:
        table = Table(title=f"Top Compounds ({len(compounds)})")
        table.add_column("ChEMBL ID", style="cyan")
        table.add_column("Name")
        table.add_column("pChEMBL", justify="right")
        table.add_column("Type")
        table.add_column("SMILES", max_width=40)
        for c in compounds:
            table.add_row(
                c.get("molecule_chembl_id", ""),
                c.get("molecule_name", "") or "",
                str(c.get("pchembl_value", "")),
                c.get("standard_type", ""),
                (c.get("canonical_smiles", "") or "")[:40],
            )
        console.print(table)
    else:
        console.print("  [yellow]No active compounds found above threshold.[/yellow]")


# ── search ───────────────────────────────────────────────────────────────────


@app.command()
def search(
    gene: str | None = typer.Option(None, "--gene", help="Gene name to search for structures."),
    organism: str | None = typer.Option(None, "--organism", help="Organism to narrow search."),
    limit: int = typer.Option(10, "--limit", help="Maximum number of results."),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result to file."),
) -> None:
    """Search RCSB PDB for experimental structures matching a gene name."""
    if not gene:
        console.print("[red]Error:[/red] --gene is required for search.")
        raise typer.Exit(2)

    try:
        summary = search_structures(gene=gene, organism=organism, limit=limit)

        console.print(f"\n[bold green]RCSB PDB search:[/bold green] {summary.get('query', '')}")
        console.print(f"  Total hits: {summary.get('total_count', 0)}")

        pdb_ids = summary.get("pdb_ids", [])
        if pdb_ids:
            console.print(f"  Top {len(pdb_ids)}: {', '.join(pdb_ids)}")
        else:
            console.print("  [yellow]No structures found.[/yellow]")

        if json_out:
            import json
            from pathlib import Path

            Path(json_out).parent.mkdir(parents=True, exist_ok=True)
            Path(json_out).write_text(json.dumps(summary, indent=2))
            console.print(f"  [green]Written to {json_out}[/green]")
        else:
            import json

            print(json.dumps(summary, indent=2))

    except BindToolError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(exc.exit_code)


# ── doctor ───────────────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Check that dependencies are available and API endpoints are reachable."""
    all_ok = True

    # Check httpx
    console.print("[bold]Checking httpx...[/bold]", end=" ")
    try:
        import httpx as _httpx

        console.print(f"[green]OK[/green] (version {_httpx.__version__})")
    except ImportError:
        console.print("[red]MISSING[/red] -- install with: pip install httpx")
        all_ok = False

    # Check protein module
    console.print("[bold]Checking bind_tools.protein module...[/bold]", end=" ")
    try:
        from bind_tools.protein import resolve_protein as _rp  # noqa: F401

        console.print("[green]OK[/green]")
    except Exception as exc:
        console.print(f"[red]FAILED[/red] ({exc})")
        all_ok = False

    # Check ligand module
    console.print("[bold]Checking bind_tools.ligand module...[/bold]", end=" ")
    try:
        from bind_tools.ligand import resolve_ligand as _rl  # noqa: F401

        console.print("[green]OK[/green]")
    except Exception as exc:
        console.print(f"[red]FAILED[/red] ({exc})")
        all_ok = False

    # Check optional RDKit (used by ligand module for SMILES 3D fallback)
    console.print("[bold]Checking RDKit (optional)...[/bold]", end=" ")
    try:
        from rdkit import Chem as _Chem  # noqa: F401

        console.print("[green]OK[/green]")
    except ImportError:
        console.print("[yellow]NOT INSTALLED[/yellow] (only needed for --smiles 3D fallback)")

    # Check rcsbsearchapi (required by protein module)
    console.print("[bold]Checking rcsbsearchapi...[/bold]", end=" ")
    try:
        import rcsbsearchapi as _rcsb  # noqa: F401

        console.print("[green]OK[/green]")
    except ImportError:
        console.print("[red]MISSING[/red] -- install with: pip install rcsbsearchapi")
        all_ok = False
    except Exception as exc:
        console.print(f"[yellow]INSTALLED but broken[/yellow] ({type(exc).__name__}: {exc})")
        all_ok = False

    # Test ChEMBL connectivity (only API still called directly)
    console.print("[bold]Testing ChEMBL API...[/bold]", end=" ")
    try:
        import httpx as _httpx

        with _httpx.Client(timeout=10, follow_redirects=True) as client:
            resp = client.get(f"{CHEMBL_BASE}/target.json?limit=1&format=json")
            if resp.status_code == 200:
                console.print(f"[green]OK[/green] (HTTP {resp.status_code})")
            else:
                console.print(f"[red]FAILED[/red] (HTTP {resp.status_code})")
                all_ok = False
    except Exception as exc:
        console.print(f"[red]FAILED[/red] ({exc})")
        all_ok = False

    if all_ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        raise typer.Exit(1)


# ── schema ───────────────────────────────────────────────────────────────────


@app.command()
def schema() -> None:
    """Print the supported result schema names for this wrapper."""
    from bind_tools.common.cli_base import print_schema

    print_schema([
        "ResolveProteinResult",
        "ResolveLigandResult",
        "ResolveBindersResult",
    ])


if __name__ == "__main__":
    app()
