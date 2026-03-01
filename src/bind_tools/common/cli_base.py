"""Shared Typer options, callbacks, and output helpers."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from .envelope import BaseRequest, BaseResult
from .errors import BindToolError

console = Console(stderr=True)
logger = logging.getLogger(__name__)


def load_request(
    request_path: str | None,
    stdin_json: bool,
    request_cls: type[BaseRequest],
    **flag_overrides: Any,
) -> BaseRequest:
    """Load a request from --request file, --stdin-json, or direct flags."""
    if request_path and stdin_json:
        console.print("[red]Cannot use both --request and --stdin-json[/red]")
        raise typer.Exit(2)

    if request_path:
        p = Path(request_path)
        if not p.is_file():
            console.print(f"[red]Request file not found: {p}[/red]")
            raise typer.Exit(3)
        raw = p.read_text()
        if p.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(raw)
        else:
            data = json.loads(raw)
        return request_cls.model_validate(data)

    if stdin_json:
        raw = sys.stdin.read()
        data = json.loads(raw)
        return request_cls.model_validate(data)

    # Build from flag overrides — filter out None values
    filtered = {k: v for k, v in flag_overrides.items() if v is not None}
    if not filtered:
        console.print("[red]Provide --request, --stdin-json, or direct flags[/red]")
        raise typer.Exit(2)
    return request_cls.model_validate(filtered)


def inject_agent_context(result: BaseResult) -> None:
    """Read BIND_AGENT_ID and BIND_RUN_ID from env and inject into result metadata."""
    agent_id = os.environ.get("BIND_AGENT_ID")
    run_id = os.environ.get("BIND_RUN_ID")
    if agent_id:
        result.metadata.agent_id = agent_id
    if run_id:
        result.metadata.run_id = run_id


def _push_to_db(result: BaseResult, json_out: str | None) -> None:
    """Record tool invocation and viz artifacts to the database. No-op if no DB."""
    try:
        from bind_tools.db import DbRecorder, is_db_available
    except ImportError:
        return
    if not is_db_available():
        return

    run_id = result.metadata.run_id or ""
    agent_id = result.metadata.agent_id
    request_id = result.metadata.request_id

    DbRecorder.record_tool_invocation(
        run_id=run_id,
        agent_id=agent_id,
        request_id=request_id,
        tool=result.tool,
        subcommand=result.kind,
        status=result.status,
        runtime_seconds=result.runtime_seconds,
        inputs=result.inputs_resolved if isinstance(result.inputs_resolved, dict) else {},
        summary=result.summary if isinstance(result.summary, dict) else {},
        errors=result.errors if isinstance(result.errors, list) else [],
    )

    _record_viz_artifacts(result, json_out)


def _record_viz_artifacts(result: BaseResult, json_out: str | None) -> None:
    """Extract viz artifact paths from a result and record them to DB."""
    from bind_tools.db import DbRecorder

    run_id = result.metadata.run_id or ""
    agent_id = result.metadata.agent_id
    request_id = result.metadata.request_id

    if result.status == "failed":
        return

    summary = result.summary if isinstance(result.summary, dict) else {}
    artifacts = result.artifacts if isinstance(result.artifacts, dict) else {}

    if result.kind == "ResolveProteinResult":
        if summary.get("fasta_path"):
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="resolve",
                artifact_type="protein_fasta", file_path=summary["fasta_path"],
                file_format="fasta", label=summary.get("protein_name"),
                metadata={"uniprot": summary.get("uniprot_accession"),
                          "gene": summary.get("gene_name")},
            )
        if summary.get("downloaded_path"):
            path = summary["downloaded_path"]
            fmt = "cif" if path.endswith(".cif") else "pdb"
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="resolve",
                artifact_type=f"protein_{fmt}", file_path=path,
                file_format=fmt, label=summary.get("protein_name"),
                metadata={"pdb_id": (summary.get("best_structures") or [{}])[0].get("pdb_id")
                          if summary.get("best_structures") else None},
            )

    elif result.kind == "ResolveLigandResult":
        if summary.get("sdf_path"):
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="resolve",
                artifact_type="ligand_sdf", file_path=summary["sdf_path"],
                file_format="sdf",
                label=summary.get("name") or summary.get("identifier"),
                metadata={"smiles": summary.get("smiles"),
                          "molecular_weight": summary.get("molecular_weight")},
            )

    elif result.kind == "BoltzPredictResult":
        if artifacts.get("primaryComplexPath"):
            affinity = summary.get("affinity") or {}
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="boltz",
                artifact_type="complex_cif",
                file_path=artifacts["primaryComplexPath"],
                file_format="cif", label="Boltz predicted complex",
                metadata={"binder_probability": affinity.get("binderProbability"),
                          "affinity_value": affinity.get("affinityValue")},
            )
        conf = artifacts.get("confidence")
        if isinstance(conf, str):
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="boltz",
                artifact_type="confidence_json", file_path=conf,
                file_format="json", label="Boltz confidence scores",
            )

    elif result.kind == "GninaResult":
        if artifacts.get("outputSdf"):
            top_pose = summary.get("topPose") or {}
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="gnina",
                artifact_type="docked_sdf",
                file_path=artifacts["outputSdf"],
                file_format="sdf",
                label=f"gnina {summary.get('mode', 'dock')} output",
                metadata={"cnn_score": top_pose.get("cnnPoseScore"),
                          "cnn_affinity": top_pose.get("cnnAffinity"),
                          "energy_kcal_mol": top_pose.get("energyKcalMol"),
                          "num_poses": summary.get("numPoses")},
            )

    elif result.kind == "PlipProfileResult":
        if artifacts.get("directory"):
            DbRecorder.record_viz_artifact(
                run_id=run_id, agent_id=agent_id, request_id=request_id,
                hypothesis_id=None, tool="plip",
                artifact_type="plip_output_dir",
                file_path=artifacts["directory"],
                file_format=None, label="PLIP interaction profile",
                metadata=summary,
            )

    # Record the JSON result envelope itself
    if json_out:
        DbRecorder.record_viz_artifact(
            run_id=run_id, agent_id=agent_id, request_id=request_id,
            hypothesis_id=None, tool=result.tool,
            artifact_type="result_json", file_path=json_out,
            file_format="json", label=f"{result.kind} result envelope",
        )


def write_result(
    result: BaseResult,
    json_out: str | None,
    yaml_out: str | None,
) -> None:
    """Write result envelope to --json-out and/or --yaml-out."""
    # Inject agent context from env vars
    inject_agent_context(result)

    # Push to DB (no-op if no DB configured or psycopg2 not installed)
    try:
        _push_to_db(result, json_out)
    except Exception as exc:
        logger.debug("DB push failed (non-fatal): %s", exc)

    result_dict = result.to_dict()
    result_json = json.dumps(result_dict, indent=2, default=str)

    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(result_json)
        console.print(f"[green]Result written to {json_out}[/green]")

    if yaml_out:
        Path(yaml_out).parent.mkdir(parents=True, exist_ok=True)
        Path(yaml_out).write_text(yaml.dump(result_dict, sort_keys=False, default_flow_style=False))
        console.print(f"[green]Result written to {yaml_out}[/green]")

    if not json_out and not yaml_out:
        # Print to stdout
        print(result_json)


def handle_error(err: BindToolError, result: BaseResult) -> BaseResult:
    """Populate a result envelope from an error."""
    result.status = "failed"
    result.errors.append(str(err))
    return result


def common_options():
    """Factory for common Typer options shared across all wrappers."""
    return {
        "request": typer.Option(None, "--request", help="YAML/JSON request file"),
        "stdin_json": typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
        "json_out": typer.Option(None, "--json-out", help="Write JSON result envelope"),
        "yaml_out": typer.Option(None, "--yaml-out", help="Write YAML result"),
        "artifacts_dir": typer.Option(None, "--artifacts-dir", help="Upstream artifacts directory"),
        "run_id": typer.Option(None, "--run-id", help="Caller-supplied run identifier"),
        "device": typer.Option(None, "--device", help="Compute device (cuda:0, cpu)"),
        "timeout_s": typer.Option(None, "--timeout-s", help="Hard timeout in seconds"),
        "dry_run": typer.Option(False, "--dry-run", help="Validate and print plan, don't execute"),
        "verbose": typer.Option(False, "--verbose", help="Verbose output"),
        "quiet": typer.Option(False, "--quiet", help="Minimal output"),
    }


def print_schema(schema_names: list[str]) -> None:
    """Print supported schema names for this wrapper."""
    for name in schema_names:
        print(name)
