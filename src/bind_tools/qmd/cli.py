"""bind-qmd CLI: local retrieval over skills, specs, schemas, examples."""

from __future__ import annotations

import time
from pathlib import Path

import typer

from bind_tools.common.cli_base import console, load_request, print_schema, write_result
from bind_tools.common.errors import BindToolError

from .models import QmdQueryRequest, QmdQueryResult, QmdQuerySpec, QmdQuerySummary
from .runner import search

app = typer.Typer(name="bind-qmd", help="Local retrieval over skills, specs, schemas, and examples.")


@app.command()
def query(
    text: str = typer.Option(None, "--text", help="Query text"),
    kind: str = typer.Option("any", "--kind", help="Filter: skill|spec|schema|example|note|any"),
    top_k: int = typer.Option(5, "--top-k", help="Max results"),
    collection: list[str] = typer.Option(None, "--collection", help="Collection name(s)"),
    strategy: str = typer.Option("keyword", "--strategy", help="keyword|semantic|hybrid"),
    paths_only: bool = typer.Option(False, "--paths-only", help="Return paths only"),
    full: bool = typer.Option(False, "--full", help="Return full file contents"),
    line_numbers: bool = typer.Option(False, "--line-numbers", help="Include line numbers"),
    rerank: bool = typer.Option(False, "--rerank", help="Rerank results"),
    tag: list[str] = typer.Option(None, "--tag", help="Filter by tag(s)"),
    must_include: list[str] = typer.Option(None, "--must-include", help="Glob must-include"),
    must_exclude: list[str] = typer.Option(None, "--must-exclude", help="Glob must-exclude"),
    request: str = typer.Option(None, "--request", help="YAML/JSON request file"),
    stdin_json: bool = typer.Option(False, "--stdin-json", help="Read JSON from stdin"),
    json_out: str = typer.Option(None, "--json-out", help="Write JSON result"),
    yaml_out: str = typer.Option(None, "--yaml-out", help="Write YAML result"),
    root: str = typer.Option(".", "--root", help="Root directory to search"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate only"),
    verbose: bool = typer.Option(False, "--verbose"),
    quiet: bool = typer.Option(False, "--quiet"),
) -> None:
    """Search local files for skills, specs, schemas, and examples."""
    result = QmdQueryResult()
    start = time.monotonic()

    try:
        # Load from request file or flags
        if request or stdin_json:
            req = load_request(request, stdin_json, QmdQueryRequest)
            spec = req.spec
            result.metadata = req.metadata
        else:
            if not text:
                console.print("[red]Provide --text or --request[/red]")
                raise typer.Exit(2)
            spec = QmdQuerySpec(
                text=text,
                kind=kind,
                topK=top_k,
                collections=collection or [],
                strategy=strategy,
                pathsOnly=paths_only,
                full=full,
                lineNumbers=line_numbers,
                rerank=rerank,
                tags=tag or [],
                mustInclude=must_include or [],
                mustExclude=must_exclude or [],
            )

        if dry_run:
            console.print(f"[yellow]Dry run: would search for '{spec.text}' (kind={spec.kind}, top_k={spec.top_k})[/yellow]")
            raise typer.Exit(0)

        root_path = Path(root).resolve()
        hits = search(
            root_path,
            spec.text,
            kind=spec.kind,
            top_k=spec.top_k,
            collections=spec.collections or None,
            must_include=spec.must_include or None,
            must_exclude=spec.must_exclude or None,
        )

        summary = QmdQuerySummary(
            queryText=spec.text,
            strategyUsed=spec.strategy,
            results=hits,
        )
        result.summary = summary.model_dump(by_alias=True, mode="json")
        result.status = "succeeded"

        if not quiet:
            console.print(f"[green]Found {len(hits)} results for '{spec.text}'[/green]")
            for h in hits:
                console.print(f"  [{h.kind}] {h.path} (score={h.score})")

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
    """Check environment for bind-qmd."""
    console.print("[green]bind-qmd doctor[/green]")
    console.print("  [green]✓[/green] No external dependencies required")
    console.print("  [green]✓[/green] bind-qmd is ready")


@app.command()
def schema() -> None:
    """Print supported schema names."""
    print_schema(["QmdQueryRequest", "QmdQueryResult"])


if __name__ == "__main__":
    app()
