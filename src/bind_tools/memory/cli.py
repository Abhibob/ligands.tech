"""Typer CLI for bind-memory: shared semantic memory for agents."""

from __future__ import annotations

import json
import time

import typer
from rich.console import Console

from bind_tools.common.cli_base import write_result

from .models import (
    MemoryAddResult,
    MemoryAddSpec,
    MemoryProfileResult,
    MemoryProfileSpec,
    MemorySearchResult,
    MemorySearchSpec,
)
from .runner import run_add, run_doctor, run_profile, run_search

app = typer.Typer(
    name="memory",
    help="Shared semantic memory for binding agents (Supermemory or local fallback).",
    no_args_is_help=True,
)
console = Console(stderr=True)


# ── add ──────────────────────────────────────────────────────────────


@app.command()
def add(
    content: str = typer.Option(..., "--content", help="Text content to store."),
    tag: str = typer.Option(..., "--tag", help="Container tag (e.g. run-20260301-abc)."),
    custom_id: str | None = typer.Option(None, "--custom-id", help="Deduplication ID."),
    metadata: str | None = typer.Option(
        None, "--metadata", help='JSON metadata string (e.g. \'{"tool":"boltz"}\').'
    ),
    entity_context: str | None = typer.Option(
        None, "--entity-context", help="Extraction hint for Supermemory (max 1500 chars)."
    ),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational output."),
) -> None:
    """Store a finding in shared memory."""
    parsed_metadata = None
    if metadata:
        try:
            parsed_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON in --metadata[/red]")
            raise typer.Exit(2)

    spec = MemoryAddSpec(
        content=content,
        containerTag=tag,
        customId=custom_id,
        metadata=parsed_metadata,
        entityContext=entity_context,
    )

    result = run_add(spec)

    if not quiet:
        if result.status == "succeeded":
            console.print(f"[green]Memory stored[/green] tag={tag}")
        else:
            console.print(f"[red]Failed:[/red] {result.errors}")

    write_result(result, json_out, None)

    if result.status == "failed":
        raise typer.Exit(4)


# ── search ───────────────────────────────────────────────────────────


@app.command()
def search(
    query: str = typer.Option(..., "--query", help="Natural language search query."),
    tag: str | None = typer.Option(None, "--tag", help="Limit search to this container tag."),
    filter_json: str | None = typer.Option(
        None, "--filter", help="JSON filter object for metadata."
    ),
    limit: int = typer.Option(10, "--limit", help="Max results to return."),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational output."),
) -> None:
    """Search shared memory for relevant findings."""
    parsed_filters = None
    if filter_json:
        try:
            parsed_filters = json.loads(filter_json)
        except json.JSONDecodeError:
            console.print("[red]Invalid JSON in --filter[/red]")
            raise typer.Exit(2)

    spec = MemorySearchSpec(
        query=query,
        containerTag=tag,
        filters=parsed_filters,
        limit=limit,
    )

    result = run_search(spec)

    if not quiet:
        if result.status == "succeeded":
            total = result.summary.get("total", 0)
            console.print(f"[green]Found {total} result(s)[/green]")
        else:
            console.print(f"[red]Failed:[/red] {result.errors}")

    write_result(result, json_out, None)

    if result.status == "failed":
        raise typer.Exit(4)


# ── profile ──────────────────────────────────────────────────────────


@app.command()
def profile(
    tag: str = typer.Option(..., "--tag", help="Container tag to profile."),
    query: str | None = typer.Option(
        None, "--query", help="Optional focus query for the profile."
    ),
    json_out: str | None = typer.Option(None, "--json-out", help="Write JSON result envelope."),
    quiet: bool = typer.Option(False, "--quiet", help="Suppress informational output."),
) -> None:
    """Generate a profile summary of all memories in a container."""
    spec = MemoryProfileSpec(containerTag=tag, query=query)

    result = run_profile(spec)

    if not quiet:
        if result.status == "succeeded":
            n = result.summary.get("num_documents", "?")
            console.print(f"[green]Profile generated[/green] ({n} documents)")
        else:
            console.print(f"[red]Failed:[/red] {result.errors}")

    write_result(result, json_out, None)

    if result.status == "failed":
        raise typer.Exit(4)


# ── doctor ───────────────────────────────────────────────────────────


@app.command()
def doctor() -> None:
    """Check memory backend connectivity and configuration."""
    info = run_doctor()
    backend = info.get("backend", "unknown")

    if info.get("status") == "ok":
        console.print(f"[green]Memory backend: {backend}[/green]")
        if backend == "local":
            console.print(f"  Memory dir: {info.get('memory_dir', '?')}")
            console.print("  Set SUPERMEMORY_API_KEY to use hosted semantic search.")
        else:
            console.print("  API key is configured and working.")
    else:
        console.print(f"[red]Memory backend error:[/red] {info.get('error', 'unknown')}")
        raise typer.Exit(4)


# ── schema ───────────────────────────────────────────────────────────


@app.command()
def schema() -> None:
    """List result schema types for this tool."""
    from bind_tools.common.cli_base import print_schema

    print_schema(["MemoryAddResult", "MemorySearchResult", "MemoryProfileResult"])
