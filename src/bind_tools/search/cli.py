"""CLI interface for web search + rerank.

Usage:
  bind-search "EGFR inhibitor mechanism" --num-results 10
  bind-search "kinase selectivity" --provider brave --verbose
  bind-search "p53 drug target" --json-out
"""

import json
import os
import sys
from typing import Optional

import httpx
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from typing_extensions import Annotated

app = typer.Typer(
    name="bind-search",
    help="Search the web and rerank results using BGE reranker via the bind-tools API.",
    add_completion=False,
)

console = Console()

DEFAULT_BASE_URL = "https://abhibob--bind-tools-gpu-webapi-serve.modal.run"


@app.command()
def query(
    search_query: Annotated[
        str, typer.Argument(help="Search query string")
    ],
    num_results: Annotated[
        int, typer.Option("--num-results", "-n", help="Number of results to return (1-20)")
    ] = 10,
    provider: Annotated[
        str, typer.Option("--provider", "-p", help="Search provider name")
    ] = "brave",
    json_out: Annotated[
        bool, typer.Option("--json-out", help="Output raw JSON instead of a table")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show snippets in results")
    ] = False,
    quiet: Annotated[
        bool, typer.Option("--quiet", "-q", help="Suppress progress output")
    ] = False,
):
    """Search the web and rerank results by relevance."""

    api_key = os.environ.get("BIND_TOOLS_API_KEY", "")
    base_url = os.environ.get("BIND_TOOLS_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        console.print(
            "[red]Error: BIND_TOOLS_API_KEY environment variable is not set[/red]",
            file=sys.stderr,
        )
        raise typer.Exit(code=1)

    url = f"{base_url.rstrip('/')}/v1/search/rerank"
    payload = {
        "query": search_query,
        "num_results": num_results,
        "provider": provider,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        if not quiet and not json_out:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(f"Searching for '{search_query}'...", total=None)
                resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)
        else:
            resp = httpx.post(url, json=payload, headers=headers, timeout=60.0)

        if resp.status_code == 401:
            console.print("[red]Error: Invalid API key[/red]", file=sys.stderr)
            raise typer.Exit(code=1)

        resp.raise_for_status()
        data = resp.json()

    except httpx.HTTPStatusError as e:
        console.print(f"[red]Error: API returned {e.response.status_code}[/red]", file=sys.stderr)
        raise typer.Exit(code=1)
    except httpx.ConnectError:
        console.print("[red]Error: Could not connect to API[/red]", file=sys.stderr)
        raise typer.Exit(code=1)

    if json_out:
        print(json.dumps(data, indent=2))
        raise typer.Exit(code=0)

    results = data.get("results", [])
    if not results:
        if not quiet:
            console.print("[yellow]No results found.[/yellow]")
        raise typer.Exit(code=0)

    table = Table(title=f"Search results for: {search_query}")
    table.add_column("Rank", style="bold", width=4)
    table.add_column("Score", width=6)
    table.add_column("Title", style="cyan", max_width=60)
    table.add_column("URL", style="dim", max_width=50)
    if verbose:
        table.add_column("Snippet", max_width=80)

    for i, r in enumerate(results, 1):
        row = [
            str(i),
            f"{r['score']:.4f}",
            r["title"],
            r["url"],
        ]
        if verbose:
            row.append(r.get("snippet", ""))
        table.add_row(*row)

    console.print(table)

    if not quiet:
        console.print(
            f"\n[dim]{data.get('num_raw', '?')} raw -> {data.get('num_reranked', '?')} reranked "
            f"(provider: {data.get('provider', provider)})[/dim]"
        )


def main():
    """Entry point for bind-search CLI."""
    app()


if __name__ == "__main__":
    main()
