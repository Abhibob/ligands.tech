"""bind-websearch CLI: web search via Exa API for research and literature discovery.

Usage:
  bind-websearch "EGFR inhibitor mechanism of action"
  bind-websearch "kinase drug resistance" --category "research paper" --num-results 5
  bind-websearch "TP53 binding compounds" --json-out results/search.json
"""

from __future__ import annotations

import time
from typing import Optional

import typer

from bind_tools.common.cli_base import console
from bind_tools.common.errors import BindToolError

from .runner import search

app = typer.Typer(
    name="bind-websearch",
    help="Search the web via Exa API for research, literature, and drug discovery information.",
    add_completion=False,
)


class WebSearchResult:
    """Minimal result envelope matching bind-tools conventions."""

    def __init__(self) -> None:
        self.api_version = "binding.dev/v1"
        self.kind = "WebSearchResult"
        self.status = "pending"
        self.summary: dict = {}
        self.artifacts: dict = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.runtime_seconds: float = 0
        self.metadata: dict = {}
        self.inputs_resolved: dict = {}
        self.parameters_resolved: dict = {}

    def to_dict(self) -> dict:
        return {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "status": self.status,
            "summary": self.summary,
            "artifacts": self.artifacts,
            "errors": self.errors,
            "warnings": self.warnings,
            "runtimeSeconds": self.runtime_seconds,
            "inputsResolved": self.inputs_resolved,
            "parametersResolved": self.parameters_resolved,
        }


@app.command()
def query(
    search_query: str = typer.Argument(help="Search query string"),
    num_results: int = typer.Option(10, "--num-results", "-n", help="Number of results (1-100)"),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Category filter: 'research paper', 'news', 'company', 'tweet', 'personal site'",
    ),
    search_type: str = typer.Option("auto", "--type", "-t", help="Search type: auto, neural, fast"),
    include_domains: Optional[list[str]] = typer.Option(
        None, "--include-domain", help="Only include results from these domains (repeatable)",
    ),
    exclude_domains: Optional[list[str]] = typer.Option(
        None, "--exclude-domain", help="Exclude results from these domains (repeatable)",
    ),
    max_chars: int = typer.Option(3000, "--max-chars", help="Max characters per result text"),
    json_out: Optional[str] = typer.Option(None, "--json-out", help="Write JSON result envelope to file"),
    yaml_out: Optional[str] = typer.Option(None, "--yaml-out", help="Write YAML result to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show full text in output"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Minimal output"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs only"),
) -> None:
    """Search the web for research papers, drug information, and scientific literature."""
    result = WebSearchResult()
    result.inputs_resolved = {"query": search_query}
    result.parameters_resolved = {
        "numResults": num_results,
        "category": category,
        "searchType": search_type,
        "maxChars": max_chars,
    }

    if dry_run:
        console.print(f"[bold]Dry-run:[/bold] would search for: {search_query}")
        console.print(f"  num_results={num_results}, category={category}, type={search_type}")
        raise typer.Exit(0)

    start = time.monotonic()
    try:
        summary = search(
            query=search_query,
            num_results=num_results,
            search_type=search_type,
            category=category,
            include_domains=include_domains,
            exclude_domains=exclude_domains,
            max_characters=max_chars,
        )
        result.summary = summary
        result.status = "succeeded"

        if not quiet:
            results = summary.get("results", [])
            console.print(f"[green]Found {len(results)} results for:[/green] {search_query}\n")
            for i, r in enumerate(results, 1):
                title = r.get("title", "Untitled")
                url = r.get("url", "")
                console.print(f"  [bold]{i}.[/bold] [cyan]{title}[/cyan]")
                console.print(f"     [dim]{url}[/dim]")

                # Show highlights or text preview
                highlights = r.get("highlights", [])
                text = r.get("text", "")
                if highlights:
                    for h in highlights[:2]:
                        console.print(f"     [italic]{h[:200]}[/italic]")
                elif verbose and text:
                    console.print(f"     {text[:300]}...")
                console.print()

    except BindToolError as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Error:[/red] {exc}")
    except Exception as exc:
        result.status = "failed"
        result.errors.append(str(exc))
        if not quiet:
            console.print(f"[red]Unexpected error:[/red] {exc}")

    result.runtime_seconds = round(time.monotonic() - start, 3)

    # Write result envelope
    if json_out or yaml_out:
        import json
        from pathlib import Path
        envelope = result.to_dict()
        if json_out:
            p = Path(json_out)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(envelope, indent=2, default=str))
            if not quiet:
                console.print(f"[dim]Result written to {json_out}[/dim]")
        if yaml_out:
            try:
                import yaml
                p = Path(yaml_out)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(yaml.dump(envelope, default_flow_style=False))
            except ImportError:
                console.print("[yellow]PyYAML not installed, skipping YAML output[/yellow]")


def main():
    """Entry point for bind-websearch CLI."""
    app()


if __name__ == "__main__":
    main()
