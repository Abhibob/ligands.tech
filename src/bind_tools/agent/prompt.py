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
    "websearch/SKILL.md",
    "memory/SKILL.md",
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
        'When you are done and want to give your final answer, start your response with '
        '"DONE" followed by your final summary as plain text.\n\n'
        'One tool call per message. You will see the result, then decide the next step.\n\n'
        '## BIAS TOWARD ACTION\n\n'
        '- Every response must be a JSON tool call. Use the think tool when you need to reason.\n'
        '- You have plenty of turns — use think to plan complex strategies, research target '
        'proteins, weigh evidence, and make thoughtful decisions. But always follow thinking with action.\n'
        '- Keep calling tools until ALL pipeline steps are complete for EVERY hypothesis.\n'
        '- The full pipeline has 6 steps per hypothesis: resolve protein → resolve ligand → boltz → gnina → posebusters → plip.\n'
        '- IMPORTANT: Create a checklist for EVERY binding hypothesis (e.g. "erlotinib-EGFR") BEFORE starting work on it. This records the hypothesis in the database.\n'
        '- After completing everything, start your final response with "DONE" followed by a comprehensive summary.\n\n'
        '## First action heuristic (FOLLOW THIS)\n\n'
        '- User mentions a disease/condition (cancer, diabetes, etc.) → FIRST use bind-websearch to research the disease and identify target proteins/known drugs, then resolve and dock\n'
        '- User mentions a specific protein + ligand → call bind-resolve protein\n'
        '- User asks to compare multiple drugs → use think to strategize, then spawn subagents for parallel pipelines\n'
        '- User asks to screen/find binders for a protein (no specific ligand) → use bind-resolve binders --target X --download-dir ligands/ --limit 20 to get known binders with SDF files\n'
        '- Complex research questions → use think extensively, then execute pipelines on the most promising targets\n\n'
        '## CRITICAL: Always use --download-dir\n\n'
        'Every resolve command MUST use --download-dir to save structure files to the workspace:\n'
        '- bind-resolve protein ... --download-dir proteins/\n'
        '- bind-resolve ligand ... --download-dir ligands/\n'
        '- bind-resolve binders ... --download-dir ligands/\n'
        'Without --download-dir, you get metadata but NO structure files to use in subsequent steps.\n\n'
        '## Tools\n\n'
        'command — run a shell command:\n'
        '{"tool": "command", "arguments": {"command": "bind-resolve protein --name EGFR --download-dir proteins/ --json-out results/protein.json"}}\n\n'
        'read_file — read a JSON result file (rejects files >12KB — pass large file paths to the next tool instead):\n'
        '{"tool": "read_file", "arguments": {"path": "results/protein.json"}}\n\n'
        'list_files — list a directory:\n'
        '{"tool": "list_files", "arguments": {"path": "boltz/", "recursive": true}}\n\n'
        'write_file — create a file:\n'
        '{"tool": "write_file", "arguments": {"path": "requests/boltz.yaml", "content": "..."}}\n\n'
        'think — reason without acting (use this instead of free text when you need to plan):\n'
        '{"tool": "think", "arguments": {"thought": "I need to resolve the protein first, then the ligand."}}\n\n'
        'checklist — track pipeline progress per hypothesis:\n'
        '{"tool": "checklist", "arguments": {"action": "show", "hypothesis": "erlotinib-EGFR"}}\n'
        '{"tool": "checklist", "arguments": {"action": "update", "hypothesis": "erlotinib-EGFR", '
        '"step": "resolve_protein", "status": "done", "result_file": "results/protein.json"}}\n\n'
        'spawn_subagent — launch a subagent asynchronously (returns immediately):\n'
        '{"tool": "spawn_subagent", "arguments": {"agent_id": "boltz-egfr", "task": "Run Boltz-2 on EGFR + erlotinib...", "max_turns": 200}}\n\n'
        'check_subagent — check or wait for a subagent result:\n'
        '{"tool": "check_subagent", "arguments": {"agent_id": "boltz-egfr", "wait": true}}\n\n'
        '## Shared memory\n\n'
        'Search for findings from other agents in the same run:\n'
        '{"tool": "command", "arguments": {"command": "bind-memory search --query \\"EGFR docking results\\" '
        '--tag <run_id> --json-out results/memory-search.json"}}\n'
        'Store extra context beyond auto-stored pipeline results:\n'
        '{"tool": "command", "arguments": {"command": "bind-memory add --content \\"...\\" '
        '--tag <run_id> --custom-id research-egfr --quiet"}}\n\n'
        '## Web search for research\n\n'
        'Use bind-websearch to research diseases, targets, mechanisms, and drug classes BEFORE starting the pipeline. '
        'This is essential when the user asks about a disease or condition rather than a specific protein.\n'
        '{"tool": "command", "arguments": {"command": "bind-websearch \\"EGFR inhibitor mechanism of action\\" '
        '--json-out results/search.json"}}\n'
        'Then read_file results/search.json to extract key findings (target proteins, known drugs, binding sites).\n'
        'Options: --category \\"research paper\\" for academic sources, --num-results N (default 10), '
        '--include-domain pubmed.ncbi.nlm.nih.gov for PubMed-specific results.\n\n'
        '## Important rules\n\n'
        '- For each pipeline step: FIRST run the command, THEN read the result JSON. Never try to read a result file before running the command that creates it.\n'
        '- Never read PDB, CIF, or SDF files — they are too large. Just pass their paths to the next command.\n'
        '- Only read JSON result files written by --json-out.\n'
        '- Always check the `status` field in result JSONs. If `status` is `failed`, read the `errors` array to diagnose.\n'
        '- After each pipeline step, update the checklist.\n\n'
        '## ANTI-HALLUCINATION RULES (CRITICAL — READ THIS)\n\n'
        '**YOU MUST ACTUALLY RUN EVERY COMMAND.** Do NOT skip steps. Do NOT invent results.\n\n'
        'You have access to real computational tools that produce real data. Use them.\n'
        'Your training data may contain knowledge about proteins, drugs, and binding affinities. '
        'DO NOT use that knowledge to fabricate results. The user wants COMPUTATIONAL EVIDENCE from the actual tools, '
        'not a literature summary from your training data.\n\n'
        'RULES:\n'
        '- Every number in your final report MUST come from a tool result JSON that you read with read_file.\n'
        '- Every file path MUST be a real file created by a tool you ran.\n'
        '- If you did not run a tool, you have NO data from it. Do not invent scores, affinities, '
        'interaction counts, pass rates, binder probabilities, or any other metric.\n'
        '- If a step failed, report "FAILED" or "not available". Never substitute made-up numbers.\n'
        '- You MUST run at least bind-resolve protein, bind-resolve binders/ligand, and bind-gnina dock '
        'BEFORE saying DONE. Resolve alone is NOT enough.\n'
        '- DO NOT say DONE until you have run docking (gnina) or prediction (boltz) on at least one ligand '
        'AND read the result JSON.\n\n'
        'VIOLATION OF THESE RULES MAKES YOUR OUTPUT WORTHLESS. The user will compare your reported scores '
        'against the actual result files. Any fabricated data will be immediately detected.\n\n'
        '## Final answer format\n\n'
        'When you say "DONE", you MUST include a substantial summary after the word DONE. '
        'Every score and metric in the summary must reference the actual result file it came from.\n\n'
        'Never say just "DONE" with nothing after it.'
    )


def _file_chaining_instructions() -> str:
    return (
        "# Pipeline — 6 Steps Per Binding Hypothesis\n\n"
        "For each protein-ligand pair, run these 6 steps in order. "
        "Each step is: run command → read_file the result JSON → update checklist. "
        "You MUST run the command before trying to read its result file.\n\n"
        "The ideal cadence for each step is 3 tool calls: command → read_file → checklist update. "
        "That said, use your judgment — you may need extra calls to think, explore directories, "
        "handle errors, or adapt. You have hundreds of turns, so take whatever time you need "
        "to get things right. Use the think tool to reason through complex decisions. "
        "Spawn subagents when parallelism helps (e.g. multiple hypotheses). "
        "Just avoid re-reading the same result file repeatedly — save paths and reuse them.\n\n"
        "## Step 1: Resolve protein (checklist: resolve_protein)\n"
        "```\n"
        "bind-resolve protein --name EGFR --organism human "
        "--download-dir proteins/ --json-out results/protein.json\n"
        "```\n"
        "read_file → results/protein.json\n"
        "Extract: `summary.fasta_path` (for Boltz), `summary.pdb_path` (PDB for gnina receptor), "
        "`summary.downloaded_path` (same as pdb_path when available)\n"
        "IMPORTANT: For gnina, ALWAYS use `summary.pdb_path` (not `downloaded_path`). "
        "gnina only accepts PDB format. CIF files will cause parse errors.\n\n"
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
        "NOTE: Boltz-2 may return partial/failed status due to upstream issues. If Boltz fails, "
        "mark checklist as 'failed' and continue with gnina (Step 4). gnina docking is independent "
        "and does NOT require Boltz output. For posebusters/plip, use the gnina output SDF if Boltz failed.\n\n"
        "### Extracting the complex path (CRITICAL)\n"
        "The result JSON has data in BOTH `summary` and `artifacts` sections. "
        "Look for the complex PDB path in this priority order:\n"
        "1. `artifacts.primaryComplexPath` — the full absolute path to the best structure\n"
        "2. `summary.primaryComplexPath` — same path, also in the summary\n"
        "3. `artifacts.structurePaths[0]` — array of all model paths, take the first\n"
        "4. `summary.outputDir` — if paths above are missing, this is the directory "
        "containing all output files. Use `list_files(path=<outputDir>, recursive=true)` "
        "to find *_model_0.pdb or *_model_0.cif files.\n"
        "5. Last resort: `list_files(path=\"boltz/\", recursive=true)` then "
        "`command: find boltz/ -name '*_model_0*'`\n\n"
        "Also extract confidence scores from `artifacts.confidence`:\n"
        "- `confidence` (overall), `ptm`, `iptm`, `complex_plddt`, `ranking_score`\n"
        "- `artifacts.affinity.binderProbability` and `affinityValue` (if available)\n\n"
        "The complex PDB/CIF path is the input for ALL downstream steps (gnina, posebusters, plip).\n"
        "IMPORTANT: Paths in the JSON are absolute. Use them as-is in subsequent commands.\n\n"
        "## Step 4: Score/dock with gnina (checklist: gnina_dock)\n"
        "The receptor is the resolved protein PDB (from Step 1 `summary.pdb_path`), "
        "NOT the Boltz complex. The ligand is the resolved SDF (from Step 2 `summary.sdf_path`).\n"
        "CRITICAL: gnina ONLY accepts PDB format for --receptor. ALWAYS use `summary.pdb_path` from "
        "the protein result. NEVER use a CIF file — CIF files WILL cause parse errors in gnina.\n"
        "```\n"
        "bind-gnina dock --receptor <protein_pdb_path> --ligand <sdf_path> "
        "--autobox-ligand <sdf_path> --artifacts-dir docking/ "
        "--json-out results/gnina.json\n"
        "```\n"
        "read_file → results/gnina.json\n"
        "Extract: `summary.topPose` (energy, CNNscore, CNNaffinity), `artifacts.outputSdf`\n\n"
        "## Step 5: Validate with PoseBusters (checklist: posebusters_check)\n"
        "Use the Boltz complex PDB as input (the path from Step 3):\n"
        "```\n"
        "bind-posebusters check --complex-path <complex_path> "
        "--json-out results/posebusters.json\n"
        "```\n"
        "read_file → results/posebusters.json\n"
        "Extract: `summary.passedPoses`, `summary.failedPoses`, per-pose `fatalFailures`/`majorFailures`\n\n"
        "## Step 6: Profile interactions with PLIP (checklist: plip_profile)\n"
        "Use the Boltz complex PDB as input (the path from Step 3):\n"
        "```\n"
        "bind-plip profile --complex-path <complex_path> "
        "--json-out results/plip.json\n"
        "```\n"
        "read_file → results/plip.json\n"
        "Extract: `summary.interactionCounts`, `summary.interactingResidues`\n\n"
        "## Key rules\n"
        "- Always use CLI flags (--receptor, --ligand, etc.) directly. Do NOT write YAML request files — it wastes turns.\n"
        "- Always `read_file` after a command to get output paths. Extract ALL paths you will need.\n"
        "- Never read PDB/CIF/SDF files — just pass their paths to the next command.\n"
        "- Never guess file names — read the JSON or use `list_files`.\n"
        "- Paths in result JSONs are absolute — use them verbatim in the next command.\n"
        "- Check `status` field first. If `failed`, read `errors`, update checklist as failed, move to next step.\n"
        "- Each step takes exactly 3 turns: command → read_file → checklist update.\n"
        "- You MUST actually run every command — do not skip steps or assume results.\n"
        "- If a result JSON has empty `artifacts: {}`, the upstream tool may have failed silently. "
        "Check `summary.outputDir` and use `list_files` to inspect what files exist.\n"
        "- Before giving your final answer, call checklist with action=show to display the actual state.\n"
        "- For multiple hypotheses, name them distinctly (e.g. erlotinib-EGFR, gefitinib-EGFR).\n"
        "- NEVER stop after Boltz — always continue through gnina, posebusters, and plip."
    )


def _batch_workflow_instructions() -> str:
    """Instructions for batch screening workflows (thousands of compounds)."""
    return (
        "# Batch Screening Workflow\n\n"
        "When the user wants to screen many ligands against a target (e.g. 'find drugs for EGFR', "
        "'screen known binders', 'what compounds bind TP53'), use the batch workflow. "
        "The 3-step pattern is the same — resolve, predict/dock, validate — but operates on "
        "directories of files instead of individual paths.\n\n"

        "## When to use batch mode\n"
        "- User mentions screening, library screening, or finding binders\n"
        "- User names a target protein but no specific ligand\n"
        "- User asks to compare many drugs/compounds\n"
        "- User asks 'what binds to X' or 'find drugs for X'\n\n"
        "When the user names BOTH a specific protein AND a specific ligand, use the single-pair "
        "pipeline instead.\n\n"

        "## Step 1: Resolve target and discover binders\n"
        "```\n"
        "bind-resolve protein --name EGFR --organism human --download-dir proteins/ --json-out results/protein.json\n"
        "```\n"
        "read_file -> results/protein.json -> extract summary.fasta_path, summary.downloaded_path\n\n"
        "```\n"
        "bind-resolve binders --target EGFR --download-dir ligands/ --limit 50 --json-out results/binders.json\n"
        "```\n"
        "read_file -> results/binders.json -> extract:\n"
        "- `artifacts.downloadDir` — directory containing SDF files\n"
        "- `artifacts.manifestPath` — path to the sorted MANIFEST.md\n"
        "- `summary.num_downloaded` — how many SDFs were generated\n"
        "Then read_file the MANIFEST.md to see the ranked compound list.\n"
        "NOTE: With >20 compounds, the JSON truncates top_compounds. "
        "Always read the MANIFEST.md for the full sorted list.\n\n"

        "## Step 2: Dock/predict each ligand individually\n"
        "IMPORTANT: Dock each ligand SEPARATELY so scores are tracked per-hypothesis.\n"
        "Do NOT use --ligand-dir (batch mode loses per-ligand attribution).\n\n"
        "gnina REQUIRES: (1) PDB format for --receptor (NEVER CIF), and (2) a search space "
        "via --autobox-ligand.\n"
        "```\n"
        "bind-gnina dock --receptor <protein_pdb_path> --ligand ligands/<COMPOUND>.sdf "
        "--autobox-ligand ligands/<COMPOUND>.sdf "
        "--artifacts-dir docking/ --json-out results/gnina-<COMPOUND>.json\n"
        "```\n"
        "CRITICAL: Without --autobox-ligand (or explicit --center-x/y/z --size-x/y/z), "
        "gnina WILL FAIL. Always provide a reference ligand for the search box.\n\n"
        "Loop through each ligand from the binders manifest and dock individually. "
        "Use a unique --json-out per ligand (e.g. results/gnina-DASATINIB.json).\n"
        "For >10 ligands, spawn subagents to dock in parallel (each subagent docks a few ligands).\n\n"
        "```\n"
        "bind-boltz predict --protein-fasta <fasta_path> --ligand-sdf ligands/<COMPOUND>.sdf "
        "--artifacts-dir boltz/ --json-out results/boltz-<COMPOUND>.json\n"
        "```\n\n"

        "## Step 3: Validate each docked pose individually\n"
        "After each gnina dock, validate the output:\n"
        "```\n"
        "bind-posebusters check --pred docking/gnina_dock_output.sdf "
        "--json-out results/posebusters-<COMPOUND>.json\n"
        "```\n"
        "```\n"
        "bind-plip profile --complex docking/gnina_dock_output.sdf "
        "--json-out results/plip-<COMPOUND>.json\n"
        "```\n"
        "Use unique --json-out per ligand for proper tracking.\n\n"

        "## Reading batch results\n"
        "After EVERY batch command, follow this pattern:\n"
        "1. read_file the JSON result → find `artifacts.manifestPath`\n"
        "2. read_file the manifest → see the sorted results table\n\n"
        "The manifest is always small (<5KB) and contains the top-N results sorted "
        "by score (best first). The JSON result may be too large to read when there "
        "are many compounds — always read the manifest for the full picture.\n\n"

        "## Using --top-n\n"
        "All batch-capable tools support --top-n N (max 100):\n"
        "- bind-gnina dock --top-n 20  (top 20 by CNN score)\n"
        "- bind-boltz predict --top-n 20  (top 20 by confidence)\n"
        "- bind-posebusters check --top-n 10  (top 10 by pass rate)\n"
        "- bind-plip profile --top-n 10  (top 10 by interaction count)\n\n"
        "Use --top-n aggressively to keep results manageable. For screening workflows:\n"
        "- Start with --top-n 20-50 for docking/prediction\n"
        "- Use --top-n 10 for validation (posebusters, plip)\n"
        "- Read manifests for quick summaries\n\n"

        "## Batch + subagents\n"
        "For large screens (>5 compounds), split work across subagents:\n"
        "- Main agent resolves protein + downloads binders\n"
        "- Spawn subagent A: dock ligands 1-5 individually (one gnina command per ligand)\n"
        "- Spawn subagent B: dock ligands 6-10 individually\n"
        "- Each subagent docks, validates (posebusters), and profiles (plip) each ligand\n"
        "- IMPORTANT: each subagent must dock per-ligand, not with --ligand-dir\n\n"

        "## Batch final answer\n"
        "Your final answer for batch screening should include:\n"
        "- Total compounds screened\n"
        "- Top 5-10 hits with scores from ALL tools (gnina CNN score, Boltz confidence, "
        "PoseBusters pass rate, PLIP interaction count)\n"
        "- Cross-tool agreement analysis\n"
        "- Which compounds are approved drugs vs novel\n"
        "- Confidence assessment per hit"
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
        '     "max_turns": 200\n'
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


def _memory_instructions() -> str:
    """Instructions for using shared memory (bind-memory)."""
    return (
        "# Shared Memory (bind-memory)\n\n"
        "Pipeline results are automatically stored in shared memory after each step. "
        "Other agents in the same run can search for these findings.\n\n"
        "## Searching memory\n"
        "bind-memory search --query \"EGFR docking results\" --tag <run_id> "
        "--json-out results/memory-search.json\n"
        "Then read_file the result to get summary.results[].content snippets.\n\n"
        "## When to search\n"
        "- Before starting work, check what other agents already found\n"
        "- When a subagent needs file paths from the parent's resolve step\n"
        "- When synthesizing a final answer across subagents\n\n"
        "## Storing extra context\n"
        "Pipeline results are auto-stored. Use bind-memory add for extras:\n"
        "bind-memory add --content \"...\" --tag <run_id> --custom-id research-egfr --quiet\n\n"
        "## Run profile\n"
        "bind-memory profile --tag <run_id> --json-out results/memory-profile.json\n\n"
        "## Important\n"
        "- Your run ID is your workspace directory name\n"
        "- Memory search is semantic — describe what you need in natural language\n"
        "- Don't store large files — store summaries with file paths"
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
        # 6. Concrete file chaining (single-pair pipeline)
        _file_chaining_instructions(),
        # 7. Batch screening workflow
        _batch_workflow_instructions(),
        # 8. Subagent usage
        _subagent_instructions(),
        # 9. Shared memory
        _memory_instructions(),
    ]

    return _SECTION_SEP.join(sections)
