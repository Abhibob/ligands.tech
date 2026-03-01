"""Typer CLI for bind-agent: LLM-powered binding analysis agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich.console import Console

from .config import AgentConfig

app = typer.Typer(
    name="bind-agent",
    help="LLM-powered agent for protein-ligand binding analysis.",
    no_args_is_help=True,
)
console = Console(stderr=True)


@app.command()
def chat(
    task: str = typer.Argument(..., help="The analysis task for the agent to perform."),
    api_key: str | None = typer.Option(None, "--api-key", help="LLM API key."),
    base_url: str | None = typer.Option(None, "--base-url", help="LLM endpoint base URL."),
    model: str | None = typer.Option(None, "--model", help="Model identifier."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace root directory."),
    run_id: str | None = typer.Option(None, "--run-id", help="Custom run identifier."),
    agent_id: str | None = typer.Option(None, "--agent-id", help="Agent identifier."),
    max_turns: int | None = typer.Option(None, "--max-turns", help="Maximum agent turns."),
    timeout: int | None = typer.Option(None, "--timeout", help="Command timeout in seconds."),
    spec_root: str | None = typer.Option(None, "--spec-root", help="Project root for spec files."),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose logging."),
    json_out: str | None = typer.Option(None, "--json-out", help="Save full AgentRun record to JSON."),
) -> None:
    """Run the agent on a binding analysis task."""
    config = AgentConfig.from_env(
        api_key=api_key,
        base_url=base_url,
        model=model,
        workspace_root=workspace,
        run_id=run_id,
        agent_id=agent_id,
        max_turns=max_turns,
        command_timeout_s=timeout,
        spec_root=spec_root,
        verbose=verbose,
    )

    if not config.api_key:
        console.print(
            "[red]Error:[/red] No API key. Set BIND_AGENT_API_KEY or "
            "OPENROUTER_API_KEY, or pass --api-key."
        )
        raise typer.Exit(3)

    # Import heavy deps only when actually running
    from .client import make_client
    from .loop import run_agent
    from .workspace import Workspace

    ws = Workspace.create(config)
    client = make_client(config)

    console.print(f"[bold]Agent run:[/bold] {config.run_id}")
    console.print(f"  Agent ID:  {config.agent_id}")
    console.print(f"  Model:     {config.model}")
    console.print(f"  Endpoint:  {config.base_url}")
    console.print(f"  Workspace: {ws.root}")
    console.print(f"  Task:      {task[:100]}{'...' if len(task) > 100 else ''}")
    console.print()

    try:
        run = run_agent(task, config, ws, client)
    except Exception as exc:
        console.print(f"[red]Agent error:[/red] {type(exc).__name__}: {exc}")
        raise typer.Exit(4)

    # Print summary
    console.print(f"\n[bold]Agent finished:[/bold] {run.status}")
    console.print(f"  Turns: {len(run.turns)}")
    console.print(
        f"  Tokens: {run.prompt_tokens} prompt + {run.completion_tokens} completion "
        f"= {run.total_tokens} total"
    )

    if run.final_response:
        console.print("\n[bold green]Final response:[/bold green]")
        print(run.final_response)

    if json_out:
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(
            json.dumps(run.model_dump(), indent=2, default=str)
        )
        console.print(f"\n[green]Run record saved to {json_out}[/green]")


@app.command()
def doctor() -> None:
    """Check that dependencies and configuration are available."""
    all_ok = True

    # Check openai SDK
    console.print("[bold]Checking openai SDK...[/bold]", end=" ")
    try:
        import openai
        console.print(f"[green]OK[/green] (version {openai.__version__})")
    except ImportError:
        console.print("[red]MISSING[/red] -- install with: uv pip install openai")
        all_ok = False

    # Check API key
    console.print("[bold]Checking API key...[/bold]", end=" ")
    config = AgentConfig.from_env()
    if config.api_key:
        masked = config.api_key[:8] + "..." + config.api_key[-4:]
        console.print(f"[green]OK[/green] ({masked})")
    else:
        console.print(
            "[yellow]NOT SET[/yellow] (set BIND_AGENT_API_KEY or OPENROUTER_API_KEY)"
        )

    # Check spec directory
    console.print("[bold]Checking spec directory...[/bold]", end=" ")
    spec_dir = Path(config.spec_root).resolve() / "binding_agent_spec"
    if spec_dir.is_dir():
        console.print(f"[green]OK[/green] ({spec_dir})")
    else:
        console.print(f"[yellow]NOT FOUND[/yellow] ({spec_dir})")

    # Check system prompt
    console.print("[bold]Checking system prompt...[/bold]", end=" ")
    prompt_path = spec_dir / "prompts" / "binding-agent-system-prompt.md"
    if prompt_path.is_file():
        console.print("[green]OK[/green]")
    else:
        console.print(f"[yellow]NOT FOUND[/yellow] ({prompt_path})")

    # Check workspace writability
    console.print("[bold]Checking workspace writability...[/bold]", end=" ")
    ws_root = Path(config.workspace_root).resolve()
    try:
        ws_root.mkdir(parents=True, exist_ok=True)
        test_file = ws_root / ".write_test"
        test_file.write_text("ok")
        test_file.unlink()
        console.print(f"[green]OK[/green] ({ws_root})")
    except OSError as exc:
        console.print(f"[red]FAILED[/red] ({exc})")
        all_ok = False

    # Check database
    console.print("[bold]Checking database...[/bold]", end=" ")
    try:
        from bind_tools.db import get_db_url, is_db_available
        if is_db_available():
            console.print(f"[green]OK[/green] (configured)")
        else:
            console.print("[yellow]NOT CONFIGURED[/yellow] (set BIND_DB_URL for tracking)")
    except ImportError:
        console.print("[yellow]NOT INSTALLED[/yellow] (install psycopg2-binary for tracking)")

    # Check endpoint reachability
    console.print("[bold]Checking endpoint...[/bold]", end=" ")
    try:
        import httpx
        with httpx.Client(timeout=10) as http:
            # Try a lightweight request to the models endpoint
            resp = http.get(
                f"{config.base_url}/models",
                headers={
                    "Authorization": f"Bearer {config.api_key}" if config.api_key else "",
                },
            )
            console.print(f"[green]OK[/green] (HTTP {resp.status_code})")
    except ImportError:
        console.print("[yellow]SKIP[/yellow] (httpx not installed)")
    except Exception as exc:
        console.print(f"[yellow]UNREACHABLE[/yellow] ({type(exc).__name__}: {exc})")

    if all_ok:
        console.print("\n[bold green]All checks passed.[/bold green]")
    else:
        console.print("\n[bold red]Some checks failed.[/bold red]")
        raise typer.Exit(1)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
