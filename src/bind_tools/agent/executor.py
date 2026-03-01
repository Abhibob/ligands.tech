"""Tool execution: subprocess for commands, filesystem for read/write/list."""

from __future__ import annotations

import json
import os
import subprocess
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .config import AgentConfig
from .workspace import Workspace


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n... [truncated at {limit} of {len(text)} chars]"


_PIPELINE_STEPS = [
    "resolve_protein",
    "resolve_ligand",
    "boltz_predict",
    "gnina_dock",
    "posebusters_check",
    "plip_profile",
]

_VALID_STATUSES = {"pending", "done", "succeeded", "failed", "skipped"}


class ToolExecutor:
    """Execute tool calls requested by the LLM."""

    def __init__(self, workspace: Workspace, config: AgentConfig) -> None:
        self.workspace = workspace
        self.config = config
        # Checklists keyed by hypothesis name.
        self._checklists: dict[str, dict[str, dict[str, Any]]] = {}
        # Async subagent pool.
        self._subagent_pool = ThreadPoolExecutor(max_workers=4)
        self._subagent_futures: dict[str, Future] = {}

    def execute(self, name: str, arguments: str) -> str:
        """Dispatch a tool call by name and return the result as a string."""
        try:
            args: dict[str, Any] = json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return json.dumps({"error": f"Invalid JSON arguments: {arguments}"})

        handler = {
            "command": self._handle_command,
            "read_file": self._handle_read_file,
            "list_files": self._handle_list_files,
            "write_file": self._handle_write_file,
            "think": self._handle_think,
            "checklist": self._handle_checklist,
            "spawn_subagent": self._handle_spawn_subagent,
            "check_subagent": self._handle_check_subagent,
        }.get(name)

        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})

        try:
            return handler(args)
        except Exception as exc:
            return json.dumps({"error": f"{type(exc).__name__}: {exc}"})

    # ── command ──────────────────────────────────────────────────────────

    def _handle_command(self, args: dict[str, Any]) -> str:
        cmd = args.get("command", "")
        if not cmd:
            return json.dumps({"error": "No command provided."})

        env = os.environ.copy()
        spec_root = Path(self.config.spec_root).resolve()
        src_path = str(spec_root / "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")

        # Inject agent and run context for CLI tools to pick up.
        env["BIND_AGENT_ID"] = self.config.agent_id
        env["BIND_RUN_ID"] = self.config.run_id

        # Propagate remote execution, API keys, and service keys to subprocesses.
        for key in ("REMOTE", "BIND_TOOLS_API_KEY", "EXA_API_KEY", "SUPERMEMORY_API_KEY"):
            if key in os.environ:
                env[key] = os.environ[key]

        # Ensure the project venv's bin is on PATH so bind-* CLIs are found.
        venv_bin = spec_root / ".venv" / "bin"
        if venv_bin.is_dir():
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")

        start = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                shell=True,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=self.config.command_timeout_s,
                env=env,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            return json.dumps({
                "exit_code": -1,
                "error": f"Command timed out after {self.config.command_timeout_s}s",
                "elapsed_s": round(elapsed, 2),
            })

        elapsed = time.monotonic() - start
        limit = self.config.max_cmd_output_chars

        # Command output is just confirmation. The real data should be in
        # --json-out files which the agent reads with read_file.
        result: dict[str, Any] = {
            "exit_code": proc.returncode,
            "elapsed_s": round(elapsed, 2),
        }

        # For success, only include stdout if it's short (e.g. ls, grep).
        # For failure, include stderr so the agent can diagnose.
        if proc.returncode == 0:
            stdout = proc.stdout.strip()
            if stdout:
                result["stdout"] = _truncate(stdout, limit)
        else:
            if proc.stderr.strip():
                result["stderr"] = _truncate(proc.stderr.strip(), limit)
            if proc.stdout.strip():
                result["stdout"] = _truncate(proc.stdout.strip(), limit)

        return json.dumps(result)

    # ── read_file ────────────────────────────────────────────────────────

    def _handle_read_file(self, args: dict[str, Any]) -> str:
        path_str = args.get("path", "")
        if not path_str:
            return json.dumps({"error": "No path provided."})

        path = self.workspace.resolve_path(path_str)
        if not path.is_file():
            return json.dumps({"error": f"File not found: {path}"})

        # Reject files that are too large — don't truncate.
        file_size = path.stat().st_size
        limit = self.config.max_read_chars
        if file_size > limit:
            return json.dumps({
                "error": f"File too large to read: {file_size} bytes (limit {limit}). "
                         f"Pass the file path directly to the next tool instead of reading it.",
                "path": str(path),
                "size": file_size,
            })

        return path.read_text(errors="replace")

    # ── list_files ───────────────────────────────────────────────────────

    def _handle_list_files(self, args: dict[str, Any]) -> str:
        path_str = args.get("path", "")
        path = self.workspace.resolve_path(path_str) if path_str else self.workspace.root
        if not path.is_dir():
            return json.dumps({"error": f"Directory not found: {path}"})

        recursive = args.get("recursive", False)
        entries: list[dict[str, Any]] = []

        items = path.rglob("*") if recursive else path.iterdir()
        for item in sorted(items):
            entry: dict[str, Any] = {
                "path": str(item.relative_to(self.workspace.root)),
                "type": "dir" if item.is_dir() else "file",
            }
            if item.is_file():
                entry["size"] = item.stat().st_size
            entries.append(entry)

        return json.dumps(entries, indent=2)

    # ── write_file ───────────────────────────────────────────────────────

    def _handle_write_file(self, args: dict[str, Any]) -> str:
        path_str = args.get("path", "")
        content = args.get("content", "")
        if not path_str:
            return json.dumps({"error": "No path provided."})

        path = self.workspace.resolve_path(path_str)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

        return json.dumps({
            "status": "ok",
            "path": str(path.relative_to(self.workspace.root)),
            "bytes_written": len(content.encode()),
        })

    # ── think ────────────────────────────────────────────────────────────

    def _handle_think(self, args: dict[str, Any]) -> str:
        thought = args.get("thought", "")
        return json.dumps({"status": "ok", "thought": thought})

    # ── checklist ─────────────────────────────────────────────────────────

    def _handle_checklist(self, args: dict[str, Any]) -> str:
        action = args.get("action", "show")
        hypothesis = args.get("hypothesis", "default")

        # Create checklist on first access.
        if hypothesis not in self._checklists:
            self._checklists[hypothesis] = {
                step: {"status": "pending", "result_file": None, "note": None}
                for step in _PIPELINE_STEPS
            }

        cl = self._checklists[hypothesis]

        if action == "show":
            return json.dumps({
                "hypothesis": hypothesis,
                "steps": {
                    step: info["status"] for step, info in cl.items()
                },
                "all_hypotheses": list(self._checklists.keys()),
            })

        if action == "update":
            step = args.get("step", "")
            if step not in cl:
                return json.dumps({"error": f"Unknown step: {step}. Valid: {_PIPELINE_STEPS}"})
            status = args.get("status", "done")
            if status not in _VALID_STATUSES:
                return json.dumps({"error": f"Invalid status: {status}. Valid: {list(_VALID_STATUSES)}"})
            cl[step]["status"] = status
            if "result_file" in args:
                cl[step]["result_file"] = args["result_file"]
            if "note" in args:
                cl[step]["note"] = args["note"]
            return json.dumps({"status": "ok", "hypothesis": hypothesis, "step": step, "new_status": status})

        return json.dumps({"error": f"Unknown action: {action}. Use 'show' or 'update'."})

    # ── spawn_subagent ────────────────────────────────────────────────

    def _handle_spawn_subagent(self, args: dict[str, Any]) -> str:
        """Spawn a child agent asynchronously in a background thread."""
        child_agent_id = args.get("agent_id", "")
        task = args.get("task", "")
        if not child_agent_id or not task:
            return json.dumps({"error": "agent_id and task are required"})

        if child_agent_id in self._subagent_futures:
            return json.dumps({"error": f"Agent '{child_agent_id}' already exists. Use check_subagent to get results."})

        role = args.get("role")
        model = args.get("model", self.config.model)
        max_turns = args.get("max_turns", 10)
        inputs = args.get("inputs")

        # Build the user message with task + optional structured inputs.
        user_message = task
        if inputs:
            user_message += f"\n\n## Inputs\n```json\n{json.dumps(inputs, indent=2)}\n```"

        # Append shared memory hint so subagents know how to search.
        memory_hint = (
            f"\n\n## Shared Memory\n"
            f"Your run ID (memory tag) is: {self.config.run_id}\n"
            f"Search shared memory: bind-memory search --query \"...\" "
            f"--tag {self.config.run_id} --json-out results/memory-search.json"
        )
        user_message += memory_hint

        # Build child config inheriting from parent.
        child_config = AgentConfig(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=model,
            workspace_root=str(self.workspace.root),
            run_id=self.config.run_id,
            agent_id=child_agent_id,
            parent_agent_id=self.config.agent_id,
            db_url=self.config.db_url,
            max_turns=max_turns,
            command_timeout_s=self.config.command_timeout_s,
            spec_root=self.config.spec_root,
            stream=False,
            verbose=self.config.verbose,
            max_cmd_output_chars=self.config.max_cmd_output_chars,
            max_read_chars=self.config.max_read_chars,
        )

        def _run_child() -> dict[str, Any]:
            from .client import make_client
            from .loop import run_agent

            child_workspace = Workspace(self.workspace.root)
            child_client = make_client(child_config)
            child_run = run_agent(user_message, child_config, child_workspace, child_client)
            return {
                "status": child_run.status,
                "agent_id": child_agent_id,
                "turns": len(child_run.turns),
                "total_tokens": child_run.total_tokens,
                "final_response": child_run.final_response[:2000] if child_run.final_response else "",
            }

        future = self._subagent_pool.submit(_run_child)
        self._subagent_futures[child_agent_id] = future

        return json.dumps({
            "status": "spawned",
            "agent_id": child_agent_id,
            "message": f"Subagent '{child_agent_id}' is running in the background. Use check_subagent to get results.",
        })

    # ── check_subagent ────────────────────────────────────────────────

    def _handle_check_subagent(self, args: dict[str, Any]) -> str:
        """Check the status of a spawned subagent, optionally waiting for it."""
        agent_id = args.get("agent_id", "")
        if not agent_id:
            return json.dumps({"error": "agent_id is required"})

        future = self._subagent_futures.get(agent_id)
        if future is None:
            known = list(self._subagent_futures.keys())
            return json.dumps({"error": f"Unknown agent_id: {agent_id}", "known_agents": known})

        wait = args.get("wait", False)

        if not future.done() and not wait:
            return json.dumps({"status": "running", "agent_id": agent_id})

        # Block until done (or already done).
        try:
            result = future.result(timeout=self.config.command_timeout_s)
            return json.dumps(result)
        except Exception as exc:
            return json.dumps({
                "status": "failed",
                "agent_id": agent_id,
                "error": f"{type(exc).__name__}: {exc}",
            })

    # ── shutdown ──────────────────────────────────────────────────────

    def shutdown(self) -> None:
        """Wait for any running subagents and clean up the thread pool."""
        self._subagent_pool.shutdown(wait=True)
