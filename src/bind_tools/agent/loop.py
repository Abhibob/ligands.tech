"""Core agent loop: messages -> LLM -> tool calls -> repeat.

Supports two tool-calling modes:
1. Native OpenAI tool_calls (when the API returns them)
2. Text-based JSON tool calls (for vLLM/custom endpoints that don't
   support native tool calling). The model outputs a JSON object like
   {"tool": "command", "arguments": {"command": "ls"}} and we parse it.
"""

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone

from openai import OpenAI
from rich.console import Console

from .config import AgentConfig
from .executor import ToolExecutor
from .models import AgentRun, ToolCall, Turn
from .prompt import build_system_prompt
from .tools import TOOLS
from .workspace import Workspace

console = Console(stderr=True)


def _parse_args(raw: str) -> dict:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


# All known tool names for matching.
_TOOL_NAMES = {"command", "read_file", "list_files", "write_file", "think", "checklist", "spawn_subagent", "check_subagent"}

# Map of unique parameter names to their tool, for inferring tool calls
# when the model outputs bare arguments without a "tool" key.
_PARAM_TO_TOOL = {
    "command": "command",
    "thought": "think",
}


def _extract_first_json(text: str) -> dict | None:
    """Extract the first valid JSON object from text using a bracket counter."""
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        c = text[i]
        if escape:
            escape = False
            continue
        if c == "\\":
            escape = True
            continue
        if c == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def _extract_text_tool_call(content: str) -> tuple[str, dict] | None:
    """Try to parse a tool call from the model's text content.

    Extracts only the FIRST JSON object — ignoring any hallucinated
    follow-up tool calls or fake results the model may have appended.

    Supports multiple formats:
    1. {"tool": "name", "arguments": {...}}       — canonical
    2. {"command": "ls -la"}                       — bare args, infer tool
    3. {"read_file": {"path": "..."}}              — tool name as key
    4. ```json ... ``` wrapped version of any above
    Returns (tool_name, arguments) or None.
    """
    if not content:
        return None

    text = content.strip()

    # Try ```json ... ``` block first
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if m:
        text = m.group(1)

    # Extract only the first JSON object
    parsed = _extract_first_json(text)
    if parsed is None:
        return None

    # Format 1: {"tool": "name", "arguments": {...}}
    if "tool" in parsed and parsed["tool"] in _TOOL_NAMES:
        tool_name = parsed["tool"]
        arguments = parsed.get("arguments", {})
        return tool_name, arguments if isinstance(arguments, dict) else {}

    # Format 3: {"read_file": {"path": "..."}} or {"command": {"command": "ls"}}
    # The model uses the tool name as the sole key, value is the arguments dict.
    if len(parsed) == 1:
        key = next(iter(parsed))
        if key in _TOOL_NAMES and isinstance(parsed[key], dict):
            return key, parsed[key]

    # Format 2: bare arguments — infer tool from parameter names.
    # {"command": "ls"} -> tool=command, args={"command": "ls"}
    # {"thought": "..."} -> tool=think, args={"thought": "..."}
    for param, tool_name in _PARAM_TO_TOOL.items():
        if param in parsed:
            return tool_name, parsed

    # {"path": "...", "content": "..."} -> write_file
    if "path" in parsed and "content" in parsed:
        return "write_file", parsed
    # {"path": "...", "recursive": ...} -> list_files
    if "path" in parsed and "recursive" in parsed:
        return "list_files", parsed
    # {"path": "..."} -> read_file
    if "path" in parsed:
        return "read_file", parsed

    return None


def run_agent(
    user_message: str,
    config: AgentConfig,
    workspace: Workspace,
    client: OpenAI,
) -> AgentRun:
    """Run the agent loop to completion."""
    system_prompt = build_system_prompt(config, workspace)
    executor = ToolExecutor(workspace, config)

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    run = AgentRun(
        run_id=config.run_id,
        agent_id=config.agent_id,
        parent_agent_id=config.parent_agent_id or "",
        workspace_root=str(workspace.root),
        model=config.model,
    )

    # Record agent start in DB (no-op if no DB).
    _db_record_agent_start(config, user_message)

    # Check if the endpoint supports native tool calling by looking at
    # the first response.  We start optimistic (pass tools) and fall
    # back to text-based if the model ignores them.
    native_tools = True

    for turn_num in range(1, config.max_turns + 1):
        console.print(f"\n[bold cyan]--- Turn {turn_num}/{config.max_turns} ---[/bold cyan]")

        # Build API kwargs
        api_kwargs: dict = {
            "model": config.model,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 8192,  # reasoning models need headroom
        }
        if native_tools:
            api_kwargs["tools"] = TOOLS
            api_kwargs["tool_choice"] = "auto"

        response = client.chat.completions.create(**api_kwargs)

        choice = response.choices[0]
        message = choice.message
        finish_reason = choice.finish_reason or ""
        content = message.content or ""

        # Track token usage
        if response.usage:
            run.prompt_tokens += response.usage.prompt_tokens or 0
            run.completion_tokens += response.usage.completion_tokens or 0
            run.total_tokens += response.usage.total_tokens or 0

        turn = Turn(
            turn_number=turn_num,
            assistant_content=content,
            finish_reason=finish_reason,
        )

        # ── Determine tool calls (native or text-based) ──

        tool_calls_to_run: list[tuple[str, str, dict]] = []  # (id, name, args)

        if message.tool_calls:
            # Native tool calling works
            for tc in message.tool_calls:
                tool_calls_to_run.append(
                    (tc.id, tc.function.name, _parse_args(tc.function.arguments))
                )
        else:
            # Try text-based parsing
            parsed = _extract_text_tool_call(content)
            if parsed:
                tool_name, arguments = parsed
                tool_calls_to_run.append(
                    (f"text-{turn_num}", tool_name, arguments)
                )
                # The model doesn't support native tool calling — stop
                # sending tools parameter to avoid confusing it.
                if native_tools and turn_num == 1:
                    native_tools = False

        # ── No tool calls: agent is done ──

        if not tool_calls_to_run:
            if content:
                preview = content if config.verbose else content[:300]
                console.print(f"[green]Agent:[/green] {preview}")
            run.final_response = content
            run.status = "completed"
            run.turns.append(turn)
            break

        # ── Execute tool calls ──

        # Append assistant message to history
        messages.append({"role": "assistant", "content": content})

        for tc_id, tc_name, tc_args in tool_calls_to_run:
            args_json = json.dumps(tc_args)

            # Progress display
            if tc_name == "command":
                console.print(f"  [yellow]$[/yellow] {tc_args.get('command', '')[:200]}")
            elif tc_name == "read_file":
                console.print(f"  [yellow]read:[/yellow] {tc_args.get('path', '?')}")
            elif tc_name == "write_file":
                console.print(f"  [yellow]write:[/yellow] {tc_args.get('path', '?')}")
            elif tc_name == "list_files":
                console.print(f"  [yellow]ls:[/yellow] {tc_args.get('path', '.')}/")
            elif tc_name == "think":
                console.print(f"  [blue]think:[/blue] {tc_args.get('thought', '')[:200]}")
            elif tc_name == "checklist":
                action = tc_args.get("action", "show")
                hyp = tc_args.get("hypothesis", "default")
                step = tc_args.get("step", "")
                if action == "update":
                    console.print(f"  [magenta]checklist:[/magenta] {hyp}/{step} -> {tc_args.get('status', 'done')}")
                else:
                    console.print(f"  [magenta]checklist:[/magenta] show {hyp}")
            elif tc_name == "spawn_subagent":
                console.print(f"  [cyan]spawn:[/cyan] {tc_args.get('agent_id', '?')} — {tc_args.get('task', '')[:100]}")
            elif tc_name == "check_subagent":
                wait = "wait" if tc_args.get("wait") else "poll"
                console.print(f"  [cyan]check:[/cyan] {tc_args.get('agent_id', '?')} ({wait})")
            else:
                console.print(f"  [yellow]{tc_name}:[/yellow] {args_json[:120]}")

            start = time.monotonic()
            result_str = executor.execute(tc_name, args_json)
            elapsed = time.monotonic() - start

            # Result display
            if tc_name == "command":
                try:
                    r = json.loads(result_str)
                    code = r.get("exit_code", "?")
                    if code == 0:
                        console.print(f"    [green]ok[/green] ({elapsed:.1f}s)")
                    else:
                        err = r.get("stderr", r.get("error", ""))
                        first_line = err.split("\n")[0][:120] if err else ""
                        console.print(f"    [red]exit {code}[/red] ({elapsed:.1f}s) {first_line}")
                except (json.JSONDecodeError, AttributeError):
                    console.print(f"    done ({elapsed:.1f}s)")
            elif tc_name == "read_file":
                console.print(f"    [dim]{len(result_str)} chars[/dim]")
            elif tc_name == "list_files":
                try:
                    entries = json.loads(result_str)
                    console.print(f"    [dim]{len(entries)} entries[/dim]")
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name == "write_file":
                try:
                    r = json.loads(result_str)
                    console.print(f"    [dim]{r.get('bytes_written', '?')} bytes[/dim]")
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name == "checklist":
                try:
                    r = json.loads(result_str)
                    if "steps" in r:
                        summary = " ".join(f"{s}:{st[0]}" for s, st in r["steps"].items())
                        console.print(f"    [dim]{summary}[/dim]")
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name in ("spawn_subagent", "check_subagent"):
                try:
                    r = json.loads(result_str)
                    status = r.get("status", "?")
                    aid = r.get("agent_id", "?")
                    if status == "spawned":
                        console.print(f"    [cyan]spawned[/cyan] {aid}")
                    elif status == "running":
                        console.print(f"    [yellow]running[/yellow] {aid}")
                    elif status in ("completed", "done"):
                        resp = r.get("final_response", "")[:80]
                        console.print(f"    [green]done[/green] {aid} ({r.get('turns', '?')} turns) {resp}")
                    elif status == "failed":
                        console.print(f"    [red]failed[/red] {aid}: {r.get('error', '')[:100]}")
                    else:
                        console.print(f"    [dim]{status}[/dim] {aid}")
                except (json.JSONDecodeError, TypeError):
                    pass

            tool_call_record = ToolCall(
                id=tc_id,
                name=tc_name,
                arguments=args_json,
                result=result_str[:4000],
                elapsed_s=round(elapsed, 2),
            )
            turn.tool_calls.append(tool_call_record)

            # Feed result back to the model.
            # For native tool calling, use the tool role.
            # For text-based, use a user message with a clear label.
            if message.tool_calls:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "content": result_str,
                })
            else:
                messages.append({
                    "role": "user",
                    "content": f"[Tool result: {tc_name}]\n{result_str}",
                })

        run.turns.append(turn)
    else:
        run.status = "max_turns"
        run.final_response = "(Agent reached maximum turns without a final response.)"

    run.finished_at = datetime.now(timezone.utc).isoformat()

    # Clean up subagent thread pool.
    executor.shutdown()

    # Record agent finish in DB (no-op if no DB).
    _db_record_agent_finish(config, run)

    return run


def _db_record_agent_start(config: AgentConfig, task: str) -> None:
    try:
        from bind_tools.db import DbRecorder, is_db_available
        if not is_db_available():
            return
        DbRecorder.record_agent_start(
            agent_id=config.agent_id,
            run_id=config.run_id,
            parent_agent_id=config.parent_agent_id,
            role=None,
            task=task[:2000],
            model=config.model,
            workspace_root=config.workspace_root,
        )
    except Exception as exc:
        console.print(f"[dim]DB record_agent_start failed (non-fatal): {exc}[/dim]")


def _db_record_agent_finish(config: AgentConfig, run: AgentRun) -> None:
    try:
        from bind_tools.db import DbRecorder, is_db_available
        if not is_db_available():
            return
        DbRecorder.record_agent_finish(
            agent_id=config.agent_id,
            status=run.status,
            total_turns=len(run.turns),
            prompt_tokens=run.prompt_tokens,
            completion_tokens=run.completion_tokens,
            total_tokens=run.total_tokens,
            final_response=run.final_response[:4000] if run.final_response else None,
        )
    except Exception as exc:
        console.print(f"[dim]DB record_agent_finish failed (non-fatal): {exc}[/dim]")
