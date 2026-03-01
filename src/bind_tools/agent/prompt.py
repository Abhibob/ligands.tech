"""System prompt assembly from Markdown sources and dynamic sections."""

from __future__ import annotations

from pathlib import Path

from .config import AgentConfig
from .workspace import Workspace

_SECTION_SEP = "\n\n---\n\n"

# SKILL files to inline (path relative to binding_agent_spec/skills/).
_SKILL_PATHS = [
    "binding-orchestrator/SKILL.md",
    "resolve/SKILL.md",
    "boltz2/SKILL.md",
    "gnina/SKILL.md",
    "posebusters/SKILL.md",
    "plip/SKILL.md",
    "qmd-search/SKILL.md",
]


def _read_optional(path: Path) -> str:
    """Read a file if it exists, otherwise return a placeholder."""
    if path.is_file():
        return path.read_text().strip()
    return f"(File not found: {path})"


def _load_skills(spec_root: Path) -> str:
    """Load all SKILL files and concatenate them."""
    skills_dir = spec_root / "binding_agent_spec" / "skills"
    parts = ["# Tool Skills\n\nReference these when deciding how to use each tool.\n"]
    for rel in _SKILL_PATHS:
        path = skills_dir / rel
        if path.is_file():
            parts.append(path.read_text().strip())
        else:
            parts.append(f"(Skill not found: {rel})")
    parts.append(
        "\nIf you need deeper context (schemas, specs, examples) beyond what is "
        "shown above, use `bind-qmd query` to retrieve additional files:\n"
        "```\nbind-qmd query --text \"boltz request schema\" --kind schema --full\n```"
    )
    return "\n\n".join(parts)


def _tool_calling_protocol() -> str:
    """Instructions for text-based tool calling."""
    return (
        '# How to Call Tools\n\n'
        'To call a tool, your ENTIRE response must be a single JSON object in this exact format:\n\n'
        '{"tool": "<name>", "arguments": {<args>}}\n\n'
        'Nothing else — no markdown, no explanation, no extra text. Just the JSON.\n\n'
        'When you are done and want to give your final answer, respond with plain text (no JSON object).\n\n'
        'One tool call per message. You will see the result, then decide the next step.\n\n'
        '## Tools\n\n'
        'command — run a shell command:\n'
        '{"tool": "command", "arguments": {"command": "bind-resolve protein --name EGFR --json-out results/protein.json"}}\n\n'
        'read_file — read a JSON result file (rejects files >12KB — pass large file paths to the next tool instead):\n'
        '{"tool": "read_file", "arguments": {"path": "results/protein.json"}}\n\n'
        'list_files — list a directory:\n'
        '{"tool": "list_files", "arguments": {"path": "boltz/"}}\n\n'
        'write_file — create a file:\n'
        '{"tool": "write_file", "arguments": {"path": "requests/boltz.yaml", "content": "..."}}\n\n'
        'think — reason without acting:\n'
        '{"tool": "think", "arguments": {"thought": "I need to resolve the protein first, then the ligand."}}\n\n'
        'checklist — track pipeline progress per hypothesis:\n'
        '{"tool": "checklist", "arguments": {"action": "show", "hypothesis": "erlotinib-EGFR"}}\n'
        '{"tool": "checklist", "arguments": {"action": "update", "hypothesis": "erlotinib-EGFR", '
        '"step": "resolve_protein", "status": "done", "result_file": "results/protein.json"}}\n\n'
        'spawn_subagent — launch a subagent asynchronously (returns immediately):\n'
        '{"tool": "spawn_subagent", "arguments": {"agent_id": "boltz-egfr", "task": "Run Boltz-2 on EGFR + erlotinib...", "max_turns": 10}}\n\n'
        'check_subagent — check or wait for a subagent result:\n'
        '{"tool": "check_subagent", "arguments": {"agent_id": "boltz-egfr", "wait": true}}\n\n'
        '## Important rules\n\n'
        '- For each pipeline step: FIRST run the command, THEN read the result JSON. Never try to read a result file before running the command that creates it.\n'
        '- Never read PDB, CIF, or SDF files — they are too large. Just pass their paths to the next command.\n'
        '- Only read JSON result files written by --json-out.\n'
        '- Always check the `status` field in result JSONs. If `status` is `failed`, read the `errors` array to diagnose.\n'
        '- After each pipeline step, update the checklist.\n'
        '- CRITICAL: NEVER fabricate, invent, or hallucinate results. If you did not run a command and read its output, you do NOT have that data. '
        'Your final report must ONLY contain data you actually received from tool results. '
        'If a step was not run or failed, say "not available" — do not invent numbers.'
    )


def _file_chaining_instructions() -> str:
    return (
        "# Pipeline — 6 Steps Per Binding Hypothesis\n\n"
        "For each protein-ligand pair, run these 6 steps in order. "
        "Each step is: run command → read_file the result JSON → update checklist. "
        "You MUST run the command before trying to read its result file.\n\n"
        "## Step 1: Resolve protein (checklist: resolve_protein)\n"
        "```\n"
        "bind-resolve protein --name EGFR --organism human "
        "--download-dir proteins/ --json-out results/protein.json\n"
        "```\n"
        "read_file → results/protein.json\n"
        "Extract: `summary.fasta_path` (for Boltz), `summary.downloaded_path` (PDB/CIF for gnina receptor)\n\n"
        "## Step 2: Resolve ligand (checklist: resolve_ligand)\n"
        "```\n"
        "bind-resolve ligand --name erlotinib "
        "--download-dir ligands/ --json-out results/ligand.json\n"
        "```\n"
        "read_file → results/ligand.json\n"
        "Extract: `summary.sdf_path` (for Boltz and gnina)\n\n"
        "## Step 3: Predict complex with Boltz-2 (checklist: boltz_predict)\n"
        "```\n"
        "bind-boltz predict --protein-fasta <fasta_path> "
        "--ligand-sdf <sdf_path> --artifacts-dir boltz/ "
        "--json-out results/boltz.json\n"
        "```\n"
        "read_file → results/boltz.json\n"
        "Extract: `summary.primaryComplexPath` (the predicted protein-ligand complex PDB)\n"
        "This complex PDB is the input for ALL downstream steps.\n"
        "If the field is missing, use `list_files(path=\"boltz/\", recursive=true)` to find *_model_0.pdb.\n\n"
        "## Step 4: Score/dock with gnina (checklist: gnina_dock)\n"
        "```\n"
        "bind-gnina dock --receptor <pdb_path> --ligand <sdf_path> "
        "--autobox-ligand <sdf_path> --artifacts-dir docking/ "
        "--json-out results/gnina.json\n"
        "```\n"
        "read_file → results/gnina.json\n"
        "Extract: `summary.topPose` (energy, CNNscore, CNNaffinity), `artifacts.outputSdf`\n\n"
        "## Step 5: Validate with PoseBusters (checklist: posebusters_check)\n"
        "Use the Boltz complex PDB as input:\n"
        "```\n"
        "bind-posebusters check --complex-path <complex_path> "
        "--json-out results/posebusters.json\n"
        "```\n"
        "read_file → results/posebusters.json\n"
        "Extract: `summary.passedPoses`, `summary.failedPoses`, per-pose `fatalFailures`/`majorFailures`\n\n"
        "## Step 6: Profile interactions with PLIP (checklist: plip_profile)\n"
        "Use the Boltz complex PDB as input:\n"
        "```\n"
        "bind-plip profile --complex-path <complex_path> "
        "--json-out results/plip.json\n"
        "```\n"
        "read_file → results/plip.json\n"
        "Extract: `summary.interactionCounts`, `summary.interactingResidues`\n\n"
        "## Key rules\n"
        "- Always use CLI flags (--receptor, --ligand, etc.) directly. Do NOT write YAML request files — it wastes turns.\n"
        "- Always `read_file` after a command to get output paths.\n"
        "- Never read PDB/CIF/SDF files — just pass their paths.\n"
        "- Never guess file names — read the JSON or use `list_files`.\n"
        "- Check `status` field first. If `failed`, update checklist as failed and move to next step. Do not retry.\n"
        "- Each step takes exactly 3 turns: command → read_file → checklist update.\n"
        "- You MUST actually run every command — do not skip steps or assume results.\n"
        "- Before giving your final answer, call checklist with action=show to display the actual state.\n"
        "- For multiple hypotheses, name them distinctly (e.g. erlotinib-EGFR, gefitinib-EGFR)."
    )


def _subagent_instructions() -> str:
    return (
        "# Subagents\n\n"
        "You can spawn subagents to explore multiple paths in parallel. Subagents are "
        "independent LLM agents with the same toolbox as you (command, read_file, "
        "write_file, list_files, think, checklist). They share your workspace directory.\n\n"
        "## When to use subagents\n\n"
        "Use subagents when you need to explore multiple paths simultaneously:\n"
        "- **Multiple binding hypotheses**: spawn one subagent per protein-ligand pair "
        "to run full pipelines in parallel\n"
        "- **Parallel pipeline steps**: after resolving inputs, spawn subagents for "
        "boltz + gnina + posebusters running at the same time\n"
        "- **Research + execution**: one subagent researches binding site info while "
        "another prepares input files\n"
        "- **Batch screening**: divide ligands across subagents for parallel screening\n\n"
        "Do NOT use subagents for single sequential tasks — just do them yourself.\n\n"
        "## How it works\n\n"
        "1. Spawn — starts running immediately in the background:\n"
        '   {"tool": "spawn_subagent", "arguments": {\n'
        '     "agent_id": "boltz-egfr-erlotinib",\n'
        '     "task": "Run the full binding pipeline (resolve protein EGFR, resolve '
        "ligand erlotinib, predict with Boltz-2, dock with gnina) and report all "
        'confidence scores. Save results to results/boltz-erlotinib.json.",\n'
        '     "max_turns": 12\n'
        "   }}\n\n"
        "2. Spawn more subagents or do other work while they run.\n\n"
        "3. Collect results:\n"
        '   {"tool": "check_subagent", "arguments": {\n'
        '     "agent_id": "boltz-egfr-erlotinib", "wait": true\n'
        "   }}\n\n"
        "## Rules\n"
        "- Give each subagent a unique, descriptive agent_id\n"
        "- Be very specific in the task — the subagent starts fresh with no memory of your conversation\n"
        "- Subagents write to the shared workspace — coordinate file paths to avoid conflicts "
        "(e.g., use subagent-specific prefixes like results/boltz-erlotinib.json)\n"
        "- After all subagents complete, synthesize their results into your final answer\n"
        "- Subagents can themselves spawn further subagents if needed"
    )


def build_system_prompt(config: AgentConfig, workspace: Workspace) -> str:
    """Assemble the full system prompt from static files and dynamic sections."""
    spec_root = Path(config.spec_root).resolve()

    sections = [
        # 1. Core identity
        _read_optional(spec_root / "binding_agent_spec" / "prompts" / "binding-agent-system-prompt.md"),
        # 2. Tool calling protocol (must come early so the model knows the format)
        _tool_calling_protocol(),
        # 3. Operating rules
        _read_optional(spec_root / "binding_agent_spec" / "AGENTS.md"),
        # 4. Workspace (cwd, dirs, workflow pattern)
        workspace.layout_description(),
        # 5. All SKILL files (inline) + qmd fallback
        _load_skills(spec_root),
        # 6. Concrete file chaining
        _file_chaining_instructions(),
        # 7. Subagent usage
        _subagent_instructions(),
    ]

    return _SECTION_SEP.join(sections)
