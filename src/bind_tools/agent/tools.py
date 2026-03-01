"""Tool definitions passed to the LLM as JSON-schema function descriptions."""

from __future__ import annotations

TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "command",
            "description": (
                "Execute a shell command in the workspace directory.\n\n"
                "Available CLIs: bind-resolve, bind-boltz, bind-posebusters, "
                "bind-gnina, bind-plip, bind-qmd.\n\n"
                "IMPORTANT: Always use --json-out results/<name>.json to save "
                "output to a file, then use read_file to inspect the result. "
                "Command stdout is truncated — the JSON file has the full data.\n\n"
                "Use --download-dir to save proteins/ligands to the pre-created "
                "workspace directories (proteins/, ligands/, etc.).\n\n"
                "Also supports standard shell commands (ls, grep, mkdir, etc.)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read a file's contents (max 12KB). Use this to read JSON result "
                "envelopes written by --json-out and extract paths/data for the "
                "next step. Rejects files larger than 12KB — pass large file paths "
                "(PDB, CIF, SDF) directly to the next command instead."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to workspace or absolute).",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List directory contents with file types and sizes. "
                "Use after running a command to discover what files were produced. "
                "Defaults to the workspace root."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (relative to workspace or absolute). "
                        "Defaults to workspace root.",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List files recursively. Default false.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Write content to a file. Parent directories are created "
                "automatically. Use for YAML request files or any workspace files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (relative to workspace or absolute).",
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "think",
            "description": (
                "Scratchpad for planning. No side effects. Use to reason about "
                "what to do next, plan multi-step workflows, or analyze results "
                "before responding."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "thought": {
                        "type": "string",
                        "description": "Your reasoning or plan.",
                    },
                },
                "required": ["thought"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checklist",
            "description": (
                "Track pipeline progress per binding hypothesis. "
                "Each hypothesis has 6 steps: resolve_protein, resolve_ligand, "
                "boltz_predict, gnina_dock, posebusters_check, plip_profile. "
                "Use action='show' to see current state, action='update' to "
                "mark a step done/failed/skipped. Always update the checklist "
                "after each pipeline step completes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Either 'show' or 'update'.",
                    },
                    "hypothesis": {
                        "type": "string",
                        "description": "Name for this binding hypothesis (e.g. 'erlotinib-EGFR').",
                    },
                    "step": {
                        "type": "string",
                        "description": "Pipeline step to update (required for action='update').",
                    },
                    "status": {
                        "type": "string",
                        "description": "New status: done, failed, skipped (default: done).",
                    },
                    "result_file": {
                        "type": "string",
                        "description": "Path to the result JSON for this step.",
                    },
                    "note": {
                        "type": "string",
                        "description": "Optional note (e.g. error message on failure).",
                    },
                },
                "required": ["action", "hypothesis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_subagent",
            "description": (
                "Launch a subagent asynchronously — returns immediately while "
                "the subagent runs in the background. Use check_subagent to "
                "poll or wait for results.\n\n"
                "Subagents are independent LLM agents with the same toolbox "
                "as you (command, read_file, write_file, etc.). They share "
                "your workspace directory.\n\n"
                "Use subagents when you need to explore multiple paths "
                "simultaneously: parallel binding hypotheses, parallel "
                "pipeline steps, research + execution split, batch screening."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique identifier for this subagent (e.g., 'boltz-egfr-erlotinib').",
                    },
                    "task": {
                        "type": "string",
                        "description": (
                            "Natural language task description. Be very specific — "
                            "the subagent starts fresh with no memory of your conversation. "
                            "Include input file paths, commands to run, and where to write results."
                        ),
                    },
                    "role": {
                        "type": "string",
                        "description": "Optional role hint: tool-runner, batch-worker, researcher, analyst.",
                    },
                    "inputs": {
                        "type": "object",
                        "description": "Structured inputs (file paths, parameters) passed as context.",
                    },
                    "model": {
                        "type": "string",
                        "description": "LLM model to use. Defaults to your model.",
                    },
                    "max_turns": {
                        "type": "integer",
                        "description": "Maximum turns for the subagent. Default 10.",
                    },
                },
                "required": ["agent_id", "task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_subagent",
            "description": (
                "Check the status of a spawned subagent. Returns immediately "
                "with {\"status\": \"running\"} if still working. "
                "Use wait=true to block until the subagent finishes and get "
                "its final response."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "The agent_id of the subagent to check.",
                    },
                    "wait": {
                        "type": "boolean",
                        "description": "If true, block until the subagent finishes. Default false.",
                    },
                },
                "required": ["agent_id"],
            },
        },
    },
]
