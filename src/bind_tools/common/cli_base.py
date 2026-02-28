"""Shared Typer options, callbacks, and output helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import typer
import yaml
from rich.console import Console

from .envelope import BaseRequest, BaseResult
from .errors import BindToolError

console = Console(stderr=True)


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


def write_result(
    result: BaseResult,
    json_out: str | None,
    yaml_out: str | None,
) -> None:
    """Write result envelope to --json-out and/or --yaml-out."""
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
