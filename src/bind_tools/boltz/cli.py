"""bind-boltz CLI: structure prediction and affinity estimation via Boltz-2."""

from __future__ import annotations

import shutil
import time
from typing import Optional

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError
from bind_tools.common.runner import detect_device

from .models import (
    BoltzConstraints,
    BoltzExecution,
    BoltzLigand,
    BoltzMsa,
    BoltzPredictRequest,
    BoltzPredictResult,
    BoltzPredictSpec,
    BoltzTarget,
)
from .runner import check_installed, run_predict

app = typer.Typer(
    name="bind-boltz",
    help="Structure prediction and affinity estimation via Boltz-2.",
)


# ── predict command ─────────────────────────────────────────────────────────


@app.command()
def predict(
    # -- Request envelope inputs --
    request: Optional[str] = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON request from stdin"),
    # -- Target --
    protein_fasta: Optional[str] = typer.Option(None, "--protein-fasta", help="Path to protein FASTA file"),
    protein_sequence: Optional[str] = typer.Option(None, "--protein-sequence", help="Inline protein amino-acid sequence"),
    protein_pdb: Optional[str] = typer.Option(None, "--protein-pdb", help="Path to protein PDB structure"),
    protein_cif: Optional[str] = typer.Option(None, "--protein-cif", help="Path to protein CIF structure"),
    # -- Ligands --
    ligand_sdf: Optional[list[str]] = typer.Option(None, "--ligand-sdf", help="Ligand SDF file (repeatable)"),
    ligand_smiles: Optional[list[str]] = typer.Option(None, "--ligand-smiles", help="Ligand SMILES string (repeatable)"),
    # -- Task --
    task: str = typer.Option("structure", "--task", help="Task: structure|affinity|both"),
    # -- MSA --
    use_msa_server: bool = typer.Option(False, "--use-msa-server", help="Use remote MSA server"),
    msa_dir: Optional[str] = typer.Option(None, "--msa-dir", help="Pre-computed MSA directory"),
    # -- Constraints --
    pocket_residue: Optional[list[str]] = typer.Option(None, "--pocket-residue", help="Pocket residue (repeatable)"),
    # -- Execution --
    top_k: int = typer.Option(1, "--top-k", help="Top-K results to keep", min=1),
    rank_by: str = typer.Option("binder-probability", "--rank-by", help="Ranking metric: binder-probability|affinity-value"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed"),
    recycling_steps: Optional[int] = typer.Option(None, "--recycling-steps", help="Number of recycling steps (>=0)"),
    diffusion_samples: Optional[int] = typer.Option(None, "--diffusion-samples", help="Number of diffusion samples (>=1)"),
    # -- Output --
    json_out: Optional[str] = typer.Option(None, "--json-out", help="Write JSON result envelope to file"),
    yaml_out: Optional[str] = typer.Option(None, "--yaml-out", help="Write YAML result to file"),
    artifacts_dir: Optional[str] = typer.Option(None, "--artifacts-dir", help="Directory for upstream artifacts"),
    # -- Runtime --
    device: Optional[str] = typer.Option(None, "--device", help="Compute device (cuda:0, cpu)"),
    timeout_s: Optional[int] = typer.Option(None, "--timeout-s", help="Hard timeout in seconds"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate and print plan, do not execute"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    quiet: bool = typer.Option(False, "--quiet", help="Minimal output"),
) -> None:
    """Run Boltz-2 structure prediction and/or affinity estimation."""
    result = BoltzPredictResult()
    start = time.monotonic()

    try:
        # -- Load spec from request file or CLI flags --
        if request or stdin_json:
            req = load_request(request, stdin_json, BoltzPredictRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            # Build target from flags
            target = BoltzTarget(
                proteinFastaPath=protein_fasta,
                proteinSequence=protein_sequence,
                proteinPdbPath=protein_pdb,
                proteinCifPath=protein_cif,
            )

            # Build ligands from flags
            ligands: list[BoltzLigand] = []
            for i, sdf in enumerate(ligand_sdf or []):
                ligands.append(BoltzLigand(id=f"L{i}", sdfPath=sdf))
            for i, smi in enumerate(ligand_smiles or []):
                ligands.append(BoltzLigand(id=f"S{i}", smiles=smi))

            # Build MSA
            msa = BoltzMsa(useServer=use_msa_server, msaDir=msa_dir)

            # Build constraints
            constraints = BoltzConstraints(
                pocketResidues=pocket_residue or [],
            )

            # Build execution
            execution = BoltzExecution(
                rankBy=rank_by,
                topK=top_k,
                seed=seed,
                recyclingSteps=recycling_steps,
                diffusionSamples=diffusion_samples,
                device=device,
            )

            spec = BoltzPredictSpec(
                target=target,
                ligands=ligands,
                task=task,
                msa=msa,
                constraints=constraints,
                execution=execution,
            )

        # Record resolved inputs
        result.inputs_resolved = {
            "proteinFastaPath": spec.target.protein_fasta_path,
            "proteinSequence": spec.target.protein_sequence[:40] + "..."
            if spec.target.protein_sequence and len(spec.target.protein_sequence) > 40
            else spec.target.protein_sequence,
            "ligandCount": len(spec.ligands),
            "task": spec.task,
        }
        result.parameters_resolved = {
            "device": device or spec.execution.device or detect_device(),
            "topK": spec.execution.top_k,
            "rankBy": spec.execution.rank_by,
            "seed": spec.execution.seed,
            "recyclingSteps": spec.execution.recycling_steps,
            "diffusionSamples": spec.execution.diffusion_samples,
            "useMsaServer": spec.msa.use_server,
        }

        if verbose and not quiet:
            console.print(f"[dim]Target: {spec.target.name or 'unnamed'}[/dim]")
            console.print(f"[dim]Ligands: {len(spec.ligands)}[/dim]")
            console.print(f"[dim]Task: {spec.task}[/dim]")
            console.print(f"[dim]Device: {result.parameters_resolved['device']}[/dim]")

        # -- Execute --
        summary = run_predict(
            spec,
            artifacts_dir=artifacts_dir,
            device=device,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )

        result.summary = summary
        result.status = "succeeded"

        if dry_run:
            if not quiet:
                console.print("[yellow]Dry run: would execute:[/yellow]")
                console.print(f"  {' '.join(summary.get('command', []))}")
            result.status = "succeeded"
        else:
            # Populate artifacts
            if "primaryComplexPath" in summary:
                result.artifacts["primaryComplexPath"] = summary["primaryComplexPath"]
            if "structurePaths" in summary:
                result.artifacts["structurePaths"] = summary["structurePaths"]
            if "confidence" in summary:
                result.artifacts["confidence"] = summary["confidence"]
            if "affinity" in summary:
                result.artifacts["affinity"] = summary["affinity"]

            if not quiet:
                console.print("[green]Boltz prediction completed successfully.[/green]")
                if "primaryComplexPath" in summary:
                    console.print(f"  Structure: {summary['primaryComplexPath']}")
                if "affinity" in summary:
                    aff = summary["affinity"]
                    if "binderProbability" in aff:
                        console.print(f"  Binder probability: {aff['binderProbability']:.4f}")
                    if "affinityValue" in aff:
                        console.print(f"  Affinity value: {aff['affinityValue']:.4f}")

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


# ── doctor command ──────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Check environment for bind-boltz: verifies boltz CLI, torch, and GPU availability."""
    console.print("[bold]bind-boltz doctor[/bold]")

    # Check boltz CLI
    if check_installed():
        console.print("  [green]OK[/green] boltz CLI found")
    else:
        console.print("  [red]MISSING[/red] boltz CLI not found on PATH")

    # Check torch
    try:
        import torch

        console.print(f"  [green]OK[/green] torch {torch.__version__}")
    except ImportError:
        console.print("  [red]MISSING[/red] torch is not installed")
        return

    # Check GPU
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        console.print(f"  [green]OK[/green] CUDA GPU available: {gpu_name}")
    else:
        console.print("  [yellow]WARN[/yellow] No CUDA GPU detected; will use CPU (slow)")

    # Detect device
    resolved_device = detect_device()
    console.print(f"  [dim]Resolved device: {resolved_device}[/dim]")


# ── schema command ──────────────────────────────────────────────────────────


@app.command()
def schema() -> None:
    """Print supported schema names for bind-boltz."""
    print_schema(["BoltzPredictRequest", "BoltzPredictResult"])


if __name__ == "__main__":
    app()
