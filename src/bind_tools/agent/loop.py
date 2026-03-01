"""Core agent loop: messages -> LLM -> tool calls -> repeat.

Supports two tool-calling modes:
1. Native OpenAI tool_calls (when the API returns them)
2. Text-based JSON tool calls (for vLLM/custom endpoints that don't
   support native tool calling). The model outputs a JSON object like
   {"tool": "command", "arguments": {"command": "ls"}} and we parse it.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

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


# ── Confidence extraction from result files ─────────────────────────

def _extract_confidence(
    step_name: str,
    result_file: str | None,
    workspace: Workspace,
) -> dict | None:
    """Read a result JSON and extract confidence scores for the pipeline step.

    Returns a dict matching what the frontend expects in pipeline_steps.confidence:
    - boltz_predict: binder_probability, affinity_value, confidence, ptm, iptm
    - gnina_dock: cnn_score, cnn_affinity, energy_kcal_mol
    - posebusters_check: pass_rate, passed_poses, total_poses
    - plip_profile: key_residues, total_interactions, interaction_counts
    """
    if not result_file:
        return None
    try:
        path = workspace.resolve_path(result_file)
        if not path.is_file() or path.stat().st_size > 50_000:
            return None
        data = json.loads(path.read_text(errors="replace"))
        summary = data.get("summary", {})
        artifacts = data.get("artifacts", {})

        if step_name == "boltz_predict":
            conf = artifacts.get("confidence", {})
            affinity = summary.get("affinity") or artifacts.get("affinity") or {}
            if isinstance(conf, str):
                conf = {}  # Path, not dict
            return {
                "binder_probability": affinity.get("binderProbability"),
                "affinity_value": affinity.get("affinityValue"),
                "confidence": conf.get("confidence") if isinstance(conf, dict) else None,
                "ptm": conf.get("ptm") if isinstance(conf, dict) else None,
                "iptm": conf.get("iptm") if isinstance(conf, dict) else None,
            }

        if step_name == "gnina_dock":
            top = summary.get("topPose") or {}
            return {
                "cnn_score": top.get("cnnPoseScore"),
                "cnn_affinity": top.get("cnnAffinity"),
                "energy_kcal_mol": top.get("energyKcalMol"),
            }

        if step_name == "posebusters_check":
            passed = summary.get("passedPoses", 0)
            total = summary.get("totalPoses") or summary.get("numPoses", 0)
            return {
                "pass_rate": passed / total if total else None,
                "passed_poses": passed,
                "total_poses": total,
            }

        if step_name == "plip_profile":
            counts = summary.get("interactionCounts", {})
            residues = summary.get("interactingResidues", [])
            return {
                "key_residues": residues[:20] if isinstance(residues, list) else [],
                "total_interactions": sum(counts.values()) if isinstance(counts, dict) else 0,
                "interaction_counts": counts,
            }

    except Exception:
        pass
    return None


# Map tool_invocation subcommand kinds to pipeline step names.
_KIND_TO_STEP = {
    "ResolveProteinResult": "resolve_protein",
    "ResolveLigandResult": "resolve_ligand",
    "BoltzPredictResult": "boltz_predict",
    "GninaResult": "gnina_dock",
    "PoseBustersCheckResult": "posebusters_check",
    "PlipProfileResult": "plip_profile",
}


def _backfill_pipeline_steps(
    run_id: str,
    subagent_id: str,
    workspace: Workspace,
) -> None:
    """Backfill pipeline_steps from tool_invocations when a subagent completes.

    Reads tool_invocations for the subagent, extracts confidence scores from
    result JSON files in the workspace, and inserts pipeline_steps rows
    linked to the hypothesis.
    """
    try:
        from bind_tools.db.connection import get_connection, is_db_available
        from bind_tools.db.recorder import DbRecorder

        if not is_db_available():
            return

        # Derive hypothesis_id from subagent_id.
        # e.g. "pipeline-MOBOCERTINIB" → hypothesis "run-xyz:MOBOCERTINIB"
        ligand_name = subagent_id.replace("pipeline-", "") if subagent_id.startswith("pipeline-") else subagent_id
        hypothesis_id = f"{run_id}:{ligand_name}"

        # Verify hypothesis exists and hasn't already been backfilled.
        with get_connection() as conn:
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM hypotheses WHERE id = %s", (hypothesis_id,))
                if cur.fetchone() is None:
                    return  # No hypothesis to link to
                # Check if pipeline_steps already exist (avoid duplicates).
                cur.execute(
                    "SELECT COUNT(*) FROM pipeline_steps WHERE hypothesis_id = %s",
                    (hypothesis_id,),
                )
                if cur.fetchone()[0] > 0:
                    return  # Already backfilled

        # Fetch tool invocations for this subagent.
        with get_connection() as conn:
            if conn is None:
                return
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT subcommand, status, runtime_seconds, summary
                       FROM tool_invocations
                       WHERE agent_id = %s ORDER BY created_at ASC""",
                    (subagent_id,),
                )
                rows = cur.fetchall()

        for subcommand, inv_status, runtime_s, summary_json in rows:
            step_name = _KIND_TO_STEP.get(subcommand)
            if not step_name:
                continue

            # Extract confidence from the summary stored in tool_invocations.
            confidence = _confidence_from_summary(step_name, summary_json)

            # Map tool_invocation status to pipeline_step status.
            if inv_status == "succeeded":
                step_status = "done"
            elif inv_status == "partial":
                step_status = "failed"
            else:
                step_status = inv_status

            DbRecorder.record_pipeline_step(
                hypothesis_id=hypothesis_id,
                agent_id=subagent_id,
                step_name=step_name,
                status=step_status,
                confidence=confidence,
                runtime_seconds=runtime_s,
            )

        # Update hypothesis status to completed.
        DbRecorder.record_hypothesis(
            hypothesis_id=hypothesis_id,
            run_id=run_id,
            agent_id=subagent_id,
            ligand_name=ligand_name,
            status="completed",
        )

    except Exception:
        pass  # Never block the agent loop


class _HypothesisTracker:
    """Real-time hypothesis creation from tool_invocations during the agent loop.

    Maintains state across tool calls so hypotheses appear in the UI immediately
    as the agent resolves binders and runs pipeline tools, rather than only at
    agent finish.
    """

    def __init__(self, run_id: str, agent_id: str) -> None:
        self.run_id = run_id
        self.agent_id = agent_id
        self.protein_name: str | None = None
        self.compounds: list[dict] = []  # {"name": ..., "id": ..., "sdf_path": ...}
        self._compound_names: set[str] = set()  # for dedup
        self._recorded_steps: set[str] = set()  # dedup key for pipeline_steps
        self._seen_invocations: set[str] = set()  # dedup key for invocations

    def on_tool_invocation(self, subcommand: str, status: str,
                           runtime_seconds: float | None,
                           summary: dict, inputs: dict) -> None:
        """Called after each command tool call with parsed tool_invocation data."""
        # Dedup: skip if we've already processed this exact invocation.
        inv_key = f"{subcommand}:{status}:{runtime_seconds}"
        if inv_key in self._seen_invocations:
            return
        self._seen_invocations.add(inv_key)

        try:
            from bind_tools.db.recorder import DbRecorder

            # Extract protein name from ResolveProteinResult.
            if subcommand == "ResolveProteinResult":
                self.protein_name = (
                    summary.get("gene_name")
                    or summary.get("protein_name")
                    or inputs.get("name")
                )

            # Extract compounds from ResolveBindersResult → create hypotheses.
            if subcommand == "ResolveBindersResult":
                target = summary.get("target_name") or inputs.get("gene") or inputs.get("target")
                if target and not self.protein_name:
                    self.protein_name = target
                top = summary.get("top_compounds", [])
                if isinstance(top, list):
                    for c in top:
                        if not isinstance(c, dict):
                            continue
                        name = c.get("molecule_name") or c.get("molecule_chembl_id") or ""
                        if not name or name in self._compound_names:
                            continue
                        self._compound_names.add(name)
                        compound = {
                            "id": c.get("molecule_chembl_id", ""),
                            "name": name,
                            "sdf_path": c.get("sdf_path"),
                        }
                        self.compounds.append(compound)
                        # Create hypothesis immediately.
                        hypothesis_id = f"{self.run_id}:{name}"
                        DbRecorder.record_hypothesis(
                            hypothesis_id=hypothesis_id,
                            run_id=self.run_id,
                            agent_id=self.agent_id,
                            protein_name=self.protein_name,
                            ligand_name=name,
                            status="running",
                        )

            # Extract individual ligand from ResolveLigandResult → create hypothesis.
            if subcommand == "ResolveLigandResult":
                name = summary.get("name") or inputs.get("name") or ""
                if name and name not in self._compound_names:
                    self._compound_names.add(name)
                    self.compounds.append({"id": "", "name": name, "sdf_path": summary.get("sdf_path")})
                    hypothesis_id = f"{self.run_id}:{name}"
                    DbRecorder.record_hypothesis(
                        hypothesis_id=hypothesis_id,
                        run_id=self.run_id,
                        agent_id=self.agent_id,
                        protein_name=self.protein_name,
                        ligand_name=name,
                        status="running",
                    )

            # Pipeline tools → create pipeline_steps on existing hypotheses.
            step_name = _KIND_TO_STEP.get(subcommand)
            if step_name and step_name not in ("resolve_protein", "resolve_ligand") and self.compounds:
                # Try to match to a specific ligand from the inputs/summary.
                # If we can't match, skip — don't broadcast aggregate scores
                # to all hypotheses (which produces identical scores everywhere).
                specific_ligand = self._match_ligand_from_invocation(summary, inputs)
                if specific_ligand:
                    step_status = "done" if status == "succeeded" else ("failed" if status == "partial" else status)
                    confidence = _confidence_from_summary(step_name, summary)
                    hypothesis_id = f"{self.run_id}:{specific_ligand}"
                    dedup_key = f"{hypothesis_id}:{step_name}:{status}:{runtime_seconds}"
                    if dedup_key not in self._recorded_steps:
                        self._recorded_steps.add(dedup_key)
                        DbRecorder.record_pipeline_step(
                            hypothesis_id=hypothesis_id,
                            agent_id=self.agent_id,
                            step_name=step_name,
                            status=step_status,
                            confidence=confidence,
                            runtime_seconds=runtime_seconds,
                        )

        except Exception:
            pass  # Never block the agent loop

    def _match_ligand_from_invocation(self, summary: dict, inputs: dict) -> str | None:
        """Try to match a tool invocation to a specific ligand hypothesis."""
        from pathlib import Path as _Path

        # 1. Check if summary mentions a specific ligand name directly.
        for field in ("ligandName", "ligand_name", "name"):
            val = summary.get(field)
            if isinstance(val, str) and val in self._compound_names:
                return val

        # 2. Check single ligand path from inputs (e.g. gnina --ligand <path>).
        ligand_path = inputs.get("ligand") or inputs.get("ligandSdf") or ""
        if isinstance(ligand_path, str) and ligand_path:
            stem = _Path(ligand_path).stem.upper()
            for c in self.compounds:
                if c["name"].upper() == stem or c["id"].upper() == stem:
                    return c["name"]

        # 3. If inputs has exactly 1 ligandPath, match from that.
        ligand_paths = inputs.get("ligandPaths") or []
        if isinstance(ligand_paths, list) and len(ligand_paths) == 1:
            stem = _Path(ligand_paths[0]).stem.upper()
            for c in self.compounds:
                if c["name"].upper() == stem or c["id"].upper() == stem:
                    return c["name"]

        # 4. If predictedPoses has exactly 1 path, try to match its stem.
        pred_poses = inputs.get("predictedPoses") or []
        if isinstance(pred_poses, list) and len(pred_poses) == 1:
            stem = _Path(pred_poses[0]).stem.upper()
            for c in self.compounds:
                if c["name"].upper() == stem or c["id"].upper() == stem:
                    return c["name"]

        return None

    def finalize(self) -> None:
        """Mark all hypotheses as completed at agent finish."""
        try:
            from bind_tools.db.recorder import DbRecorder
            for compound in self.compounds:
                hypothesis_id = f"{self.run_id}:{compound['name']}"
                DbRecorder.record_hypothesis(
                    hypothesis_id=hypothesis_id,
                    run_id=self.run_id,
                    agent_id=self.agent_id,
                    protein_name=self.protein_name,
                    ligand_name=compound["name"],
                    status="completed",
                )
        except Exception:
            pass


def _feed_new_invocations_to_tracker(
    tracker: _HypothesisTracker,
    agent_id: str,
) -> None:
    """Query DB for tool_invocations and feed them to the hypothesis tracker.

    The tracker deduplicates internally, so it's safe to call this repeatedly
    with all invocations.
    """
    try:
        from bind_tools.db.connection import get_connection, is_db_available
        if not is_db_available():
            return

        with get_connection() as conn:
            if conn is None:
                return
            import psycopg2.extras
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT subcommand, status, runtime_seconds, summary, inputs
                       FROM tool_invocations
                       WHERE agent_id = %s
                       ORDER BY created_at ASC""",
                    (agent_id,),
                )
                rows = [dict(r) for r in cur.fetchall()]

        for row in rows:
            summary = row.get("summary")
            if isinstance(summary, str):
                try:
                    summary = json.loads(summary)
                except (json.JSONDecodeError, TypeError):
                    summary = {}
            elif summary is None:
                summary = {}

            inputs = row.get("inputs")
            if isinstance(inputs, str):
                try:
                    inputs = json.loads(inputs)
                except (json.JSONDecodeError, TypeError):
                    inputs = {}
            elif inputs is None:
                inputs = {}

            tracker.on_tool_invocation(
                subcommand=row.get("subcommand", ""),
                status=row.get("status", ""),
                runtime_seconds=row.get("runtime_seconds"),
                summary=summary,
                inputs=inputs,
            )
    except Exception:
        pass  # Never block the agent loop


def _confidence_from_summary(step_name: str, summary_json: str | dict | None) -> dict | None:
    """Extract confidence dict from tool_invocations.summary JSON."""
    if not summary_json:
        return None
    try:
        summary = summary_json if isinstance(summary_json, dict) else json.loads(summary_json)
    except (json.JSONDecodeError, TypeError):
        return None

    if step_name == "boltz_predict":
        affinity = summary.get("affinity") or {}
        return {
            "binder_probability": affinity.get("binderProbability"),
            "affinity_value": affinity.get("affinityValue"),
            "confidence": summary.get("confidence"),
            "ptm": summary.get("ptm"),
            "iptm": summary.get("iptm"),
        }

    if step_name == "gnina_dock":
        top = summary.get("topPose") or {}
        return {
            "cnn_score": top.get("cnnPoseScore"),
            "cnn_affinity": top.get("cnnAffinity"),
            "energy_kcal_mol": top.get("energyKcalMol"),
        }

    if step_name == "posebusters_check":
        passed = summary.get("passedPoses", 0)
        total = summary.get("totalPoses") or summary.get("numPoses", 0)
        return {
            "pass_rate": passed / total if total else None,
            "passed_poses": passed,
            "total_poses": total,
        }

    if step_name == "plip_profile":
        counts = summary.get("interactionCounts", {})
        residues = summary.get("interactingResidues", [])
        return {
            "key_residues": residues[:20] if isinstance(residues, list) else [],
            "total_interactions": sum(counts.values()) if isinstance(counts, dict) else 0,
            "interaction_counts": counts,
        }

    return None


# ── Event publishing helper ──────────────────────────────────────────

def _publish(agent_id: str, event_type: str, **data: object) -> None:
    """Publish an event to the event bus (non-fatal if unavailable)."""
    try:
        from bind_tools.api.events import AgentEvent, AgentEventBus
        AgentEventBus.get().publish(AgentEvent(
            agent_id=agent_id,
            event_type=event_type,
            data=data,
        ))
    except Exception:
        pass  # Event bus not available (e.g., running standalone)


# ── Auto-store pipeline results to shared memory ─────────────────────

_PIPELINE_PREFIXES = (
    "bind-resolve",
    "bind-boltz",
    "bind-gnina",
    "bind-posebusters",
    "bind-plip",
)

# Map command prefix to tool name for metadata.
_PREFIX_TO_TOOL = {
    "bind-resolve": "resolve",
    "bind-boltz": "boltz",
    "bind-gnina": "gnina",
    "bind-posebusters": "posebusters",
    "bind-plip": "plip",
}


def _is_pipeline_command(cmd: str) -> bool:
    """Check if a command string is a pipeline tool invocation."""
    stripped = cmd.strip()
    return any(stripped.startswith(prefix) for prefix in _PIPELINE_PREFIXES)


def _extract_json_out_path(cmd: str) -> str | None:
    """Extract the --json-out path from a command string."""
    # Match --json-out followed by the path argument.
    m = re.search(r"--json-out\s+(\S+)", cmd)
    return m.group(1) if m else None


def _build_memory_content(tool_name: str, summary: dict, artifacts: dict) -> str:
    """Build a Markdown summary of key metrics for memory storage."""
    lines: list[str] = []

    if tool_name == "resolve":
        gene = summary.get("gene_name") or summary.get("name", "")
        if gene:
            lines.append(f"Resolved: {gene}")
        fasta = summary.get("fasta_path")
        if fasta:
            lines.append(f"FASTA: {fasta}")
        pdb = summary.get("pdb_path") or summary.get("downloaded_path")
        if pdb:
            lines.append(f"PDB: {pdb}")
        sdf = summary.get("sdf_path")
        if sdf:
            lines.append(f"SDF: {sdf}")

    elif tool_name == "boltz":
        affinity = summary.get("affinity") or artifacts.get("affinity") or {}
        bp = affinity.get("binderProbability")
        if bp is not None:
            lines.append(f"Binder probability: {bp}")
        av = affinity.get("affinityValue")
        if av is not None:
            lines.append(f"Affinity value: {av}")
        conf = artifacts.get("confidence")
        if isinstance(conf, dict):
            lines.append(f"Confidence: {conf.get('confidence')}")
        cpath = artifacts.get("primaryComplexPath")
        if cpath:
            lines.append(f"Complex path: {cpath}")

    elif tool_name == "gnina":
        top = summary.get("topPose") or {}
        cnn = top.get("cnnPoseScore")
        if cnn is not None:
            lines.append(f"CNN score: {cnn}")
        aff = top.get("cnnAffinity")
        if aff is not None:
            lines.append(f"CNN affinity: {aff}")
        energy = top.get("energyKcalMol")
        if energy is not None:
            lines.append(f"Energy: {energy} kcal/mol")
        out_sdf = artifacts.get("outputSdf")
        if out_sdf:
            lines.append(f"Output SDF: {out_sdf}")

    elif tool_name == "posebusters":
        passed = summary.get("passedPoses", 0)
        total = summary.get("totalPoses") or summary.get("numPoses", 0)
        lines.append(f"PoseBusters: {passed}/{total} passed")
        failures = summary.get("fatalFailures") or summary.get("majorFailures")
        if failures:
            lines.append(f"Failures: {failures}")

    elif tool_name == "plip":
        counts = summary.get("interactionCounts", {})
        if counts:
            lines.append(f"Interactions: {counts}")
        residues = summary.get("interactingResidues", [])
        if residues:
            lines.append(f"Key residues: {', '.join(str(r) for r in residues[:10])}")

    return "\n".join(lines) if lines else f"{tool_name} result completed."


def _build_memory_metadata(
    tool_name: str, summary: dict, artifacts: dict, agent_id: str
) -> dict[str, str | int | float | bool]:
    """Build flat metadata dict for memory storage."""
    meta: dict[str, str | int | float | bool] = {"tool": tool_name, "agent_id": agent_id}

    if tool_name == "resolve":
        target = summary.get("gene_name") or summary.get("name")
        if target:
            meta["target"] = target

    elif tool_name == "boltz":
        affinity = summary.get("affinity") or artifacts.get("affinity") or {}
        bp = affinity.get("binderProbability")
        if bp is not None:
            meta["binder_probability"] = bp

    elif tool_name == "gnina":
        top = summary.get("topPose") or {}
        cnn = top.get("cnnPoseScore")
        if cnn is not None:
            meta["cnn_score"] = cnn
        energy = top.get("energyKcalMol")
        if energy is not None:
            meta["energy"] = energy

    elif tool_name == "posebusters":
        passed = summary.get("passedPoses", 0)
        total = summary.get("totalPoses") or summary.get("numPoses", 0)
        meta["pb_all_pass"] = passed == total and total > 0

    elif tool_name == "plip":
        counts = summary.get("interactionCounts", {})
        if isinstance(counts, dict):
            meta["total_interactions"] = sum(counts.values())

    return meta


def _auto_store_memory(config: AgentConfig, cmd: str, workspace: Workspace) -> None:
    """Fire-and-forget: store pipeline result summary in shared memory.

    Reads the --json-out file from the command, builds a summary, and
    spawns ``bind-memory add`` as a non-blocking Popen. Best-effort only.
    """
    try:
        json_out_path = _extract_json_out_path(cmd)
        if not json_out_path:
            return

        result_path = workspace.resolve_path(json_out_path)
        if not result_path.is_file() or result_path.stat().st_size > 100_000:
            return

        data = json.loads(result_path.read_text(errors="replace"))
        summary = data.get("summary", {})
        artifacts = data.get("artifacts", {})
        status = data.get("status", "")
        if status == "failed":
            return

        # Determine tool name from command.
        stripped = cmd.strip()
        tool_name = "unknown"
        for prefix, name in _PREFIX_TO_TOOL.items():
            if stripped.startswith(prefix):
                tool_name = name
                break

        content = _build_memory_content(tool_name, summary, artifacts)
        if not content:
            return

        meta = _build_memory_metadata(tool_name, summary, artifacts, config.agent_id)
        custom_id = f"{tool_name}-{config.agent_id}"

        # Build the bind-memory add command.
        mem_cmd = [
            "bind-memory", "add",
            "--content", content,
            "--tag", config.run_id,
            "--custom-id", custom_id,
            "--metadata", json.dumps(meta),
            "--quiet",
        ]

        # Propagate environment.
        env = os.environ.copy()
        spec_root = Path(config.spec_root).resolve()
        venv_bin = spec_root / ".venv" / "bin"
        if venv_bin.is_dir():
            env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
        env["BIND_TOOLS_WORKSPACE"] = str(workspace.root)

        # Fire-and-forget (non-blocking).
        subprocess.Popen(
            mem_cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(workspace.root),
            env=env,
        )
    except Exception:
        pass  # Best-effort — never block the agent loop


# ── Main agent loop ──────────────────────────────────────────────────

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

    # Publish start event.
    _publish(config.agent_id, "agent_start", task=user_message[:500])

    # Check if the endpoint supports native tool calling by looking at
    # the first response.  We start optimistic (pass tools) and fall
    # back to text-based if the model ignores them.
    native_tools = True
    nudge_count = 0  # Track how many times we've nudged the agent to act
    command_count = 0  # Track how many command tool calls have been executed
    hyp_tracker = _HypothesisTracker(config.run_id, config.agent_id)

    for turn_num in range(1, config.max_turns + 1):
        console.print(f"\n[bold cyan]--- Turn {turn_num}/{config.max_turns} ---[/bold cyan]")
        _publish(config.agent_id, "turn_start", turn=turn_num, maxTurns=config.max_turns)

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

        # ── No tool calls found ──

        if not tool_calls_to_run:
            # If there's still plenty of turns left, the model may have
            # responded with a plan/explanation instead of a tool call.
            # Re-prompt it to take action rather than just stopping.
            remaining = config.max_turns - turn_num
            # Reject premature "DONE" — the model must run at least 3 commands
            # (resolve protein + resolve binders/ligand + gnina/boltz) before finishing.
            # This prevents the LLM from hallucinating results using training knowledge.
            MIN_COMMANDS_BEFORE_DONE = 3
            is_premature_done = (
                content
                and content.strip().startswith("DONE")
                and command_count < MIN_COMMANDS_BEFORE_DONE
                and remaining > 10
            )

            should_nudge = (
                remaining > 2
                and nudge_count < 5
                and content
                and (not content.strip().startswith("DONE") or is_premature_done)
            )

            if should_nudge:
                nudge_count += 1
                messages.append({"role": "assistant", "content": content})

                if is_premature_done:
                    console.print(f"  [red]REJECTED premature DONE — only {command_count} commands run (need ≥{MIN_COMMANDS_BEFORE_DONE})[/red]")
                    _publish(config.agent_id, "nudge", count=nudge_count,
                             text=f"Rejected premature DONE ({command_count} commands)")
                    nudge_msg = (
                        f"REJECTED: You said DONE but you have only run {command_count} commands. "
                        "You MUST run the full pipeline before finishing. "
                        "Your output contains HALLUCINATED data — scores and files that don't exist. "
                        "This is NOT acceptable. You must:\n"
                        "1. Run bind-resolve binders (or bind-resolve ligand) to get ligand SDF files\n"
                        "2. Run bind-gnina dock to get REAL docking scores\n"
                        "3. Run bind-posebusters check for validation\n"
                        "4. Run bind-plip profile for interaction analysis\n"
                        "5. Read each result JSON to get REAL numbers\n\n"
                        "Start NOW by calling the next command. Do NOT say DONE again until "
                        "you have actual tool results."
                    )
                else:
                    console.print(f"  [yellow]no tool call detected — nudging agent to act ({nudge_count}/5)[/yellow]")
                    _publish(config.agent_id, "nudge", count=nudge_count, text=content[:500])
                    if nudge_count == 1:
                        nudge_msg = (
                            "You responded with text instead of calling a tool. "
                            "Do NOT plan — ACT. Your response must be ONLY a JSON object like:\n"
                            '{"tool": "command", "arguments": {"command": "bind-resolve protein --name EGFR --download-dir proteins/ --json-out results/protein.json"}}\n\n'
                            "No other text. Just the JSON. Call the next tool NOW."
                        )
                    elif nudge_count == 2:
                        nudge_msg = (
                            "STOP writing text. You MUST respond with ONLY a JSON tool call. "
                            "If you don't know what to do next, use the think tool:\n"
                            '{"tool": "think", "arguments": {"thought": "I need to figure out the next step"}}\n\n'
                            "Then call the next command on the following turn. DO IT NOW."
                        )
                    elif nudge_count <= 4:
                        nudge_msg = (
                            "You keep responding with text. ONLY JSON tool calls are accepted.\n"
                            "Here is exactly what to type — copy it:\n"
                            '{"tool": "think", "arguments": {"thought": "planning next step"}}\n'
                        )
                    else:
                        nudge_msg = (
                            "FINAL WARNING: Respond with a JSON tool call or I will terminate you.\n"
                            '{"tool": "think", "arguments": {"thought": "planning next step"}}\n'
                            "ONLY JSON. NO OTHER TEXT."
                        )
                messages.append({"role": "user", "content": nudge_msg})
                run.turns.append(turn)
                continue

            if content:
                # Strip any "DONE" prefix from the final response
                final = content.strip()
                if final.startswith("DONE"):
                    final = final[4:].strip()
                # If stripping "DONE" left nothing, use original content
                if not final:
                    final = content.strip()
                preview = final if config.verbose else final[:300]
                console.print(f"[green]Agent:[/green] {preview}")
                run.final_response = final
            else:
                run.final_response = "(Agent completed without a final response.)"
            run.status = "completed"
            run.turns.append(turn)
            _publish(config.agent_id, "done", status="completed",
                     turns=turn_num, finalResponse=(run.final_response or "")[:1000])
            break

        # ── Execute tool calls ──

        nudge_count = 0  # Reset nudge counter on successful tool call
        for _, tc_name_check, _ in tool_calls_to_run:
            if tc_name_check == "command":
                command_count += 1

        # Append assistant message to history
        messages.append({"role": "assistant", "content": content})

        # If the assistant sent text alongside the tool call, publish it
        if content and not content.strip().startswith("{"):
            _publish(config.agent_id, "assistant_text", text=content[:1000])

        for tc_id, tc_name, tc_args in tool_calls_to_run:
            args_json = json.dumps(tc_args)

            # Build a human-readable summary for display and events
            if tc_name == "command":
                display = tc_args.get("command", "")[:200]
                console.print(f"  [yellow]$[/yellow] {display}")
            elif tc_name == "read_file":
                display = tc_args.get("path", "?")
                console.print(f"  [yellow]read:[/yellow] {display}")
            elif tc_name == "write_file":
                display = tc_args.get("path", "?")
                console.print(f"  [yellow]write:[/yellow] {display}")
            elif tc_name == "list_files":
                display = f"{tc_args.get('path', '.')}/"
                console.print(f"  [yellow]ls:[/yellow] {display}")
            elif tc_name == "think":
                display = tc_args.get("thought", "")[:500]
                console.print(f"  [blue]think:[/blue] {display[:200]}")
            elif tc_name == "checklist":
                action = tc_args.get("action", "show")
                hyp = tc_args.get("hypothesis", "default")
                step = tc_args.get("step", "")
                if action == "update":
                    display = f"{hyp}/{step} -> {tc_args.get('status', 'done')}"
                    console.print(f"  [magenta]checklist:[/magenta] {display}")
                else:
                    display = f"show {hyp}"
                    console.print(f"  [magenta]checklist:[/magenta] {display}")
            elif tc_name == "spawn_subagent":
                display = f"{tc_args.get('agent_id', '?')} — {tc_args.get('task', '')[:100]}"
                console.print(f"  [cyan]spawn:[/cyan] {display}")
            elif tc_name == "check_subagent":
                wait = "wait" if tc_args.get("wait") else "poll"
                display = f"{tc_args.get('agent_id', '?')} ({wait})"
                console.print(f"  [cyan]check:[/cyan] {display}")
            else:
                display = args_json[:120]
                console.print(f"  [yellow]{tc_name}:[/yellow] {display}")

            # Publish tool_call event
            _publish(config.agent_id, "tool_call",
                     turn=turn_num, tool=tc_name, args=tc_args, display=display)

            start = time.monotonic()
            result_str = executor.execute(tc_name, args_json)
            elapsed = time.monotonic() - start

            # Build result summary for display and events
            result_summary = ""
            if tc_name == "command":
                try:
                    r = json.loads(result_str)
                    code = r.get("exit_code", "?")
                    if code == 0:
                        console.print(f"    [green]ok[/green] ({elapsed:.1f}s)")
                        result_summary = f"ok ({elapsed:.1f}s)"
                    else:
                        err = r.get("stderr", r.get("error", ""))
                        first_line = err.split("\n")[0][:120] if err else ""
                        console.print(f"    [red]exit {code}[/red] ({elapsed:.1f}s) {first_line}")
                        result_summary = f"exit {code}: {first_line}"
                except (json.JSONDecodeError, AttributeError):
                    console.print(f"    done ({elapsed:.1f}s)")
                    result_summary = f"done ({elapsed:.1f}s)"
                # Real-time hypothesis creation: check for new tool_invocations
                # written by the CLI subprocess and feed them to the tracker.
                try:
                    _feed_new_invocations_to_tracker(hyp_tracker, config.agent_id)
                except Exception:
                    pass
                # Auto-store pipeline results in shared memory.
                cmd_str = tc_args.get("command", "")
                if _is_pipeline_command(cmd_str):
                    _auto_store_memory(config, cmd_str, workspace)
            elif tc_name == "read_file":
                console.print(f"    [dim]{len(result_str)} chars[/dim]")
                result_summary = f"{len(result_str)} chars"
            elif tc_name == "list_files":
                try:
                    entries = json.loads(result_str)
                    console.print(f"    [dim]{len(entries)} entries[/dim]")
                    result_summary = f"{len(entries)} entries"
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name == "write_file":
                try:
                    r = json.loads(result_str)
                    console.print(f"    [dim]{r.get('bytes_written', '?')} bytes[/dim]")
                    result_summary = f"{r.get('bytes_written', '?')} bytes written"
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name == "think":
                _publish(config.agent_id, "thinking", thought=tc_args.get("thought", "")[:2000])
                result_summary = "ok"
            elif tc_name == "checklist":
                try:
                    r = json.loads(result_str)
                    if "steps" in r:
                        summary = " ".join(f"{s}:{st[0]}" for s, st in r["steps"].items())
                        console.print(f"    [dim]{summary}[/dim]")
                        result_summary = summary
                    # Record hypothesis + pipeline steps in DB.
                    action = tc_args.get("action", "show")
                    hyp = tc_args.get("hypothesis", "default")
                    if hyp != "default":
                        try:
                            from bind_tools.db.recorder import DbRecorder
                            hypothesis_id = f"{config.run_id}:{hyp}"
                            parts = hyp.split("-", 1)
                            ligand_name = parts[0] if len(parts) >= 1 else None
                            protein_name = parts[1] if len(parts) >= 2 else None
                            hyp_status = "running" if action == "update" else "pending"
                            DbRecorder.record_hypothesis(
                                hypothesis_id=hypothesis_id,
                                run_id=config.run_id,
                                agent_id=config.agent_id,
                                protein_name=protein_name,
                                ligand_name=ligand_name,
                                status=hyp_status,
                            )
                            # On checklist update, also record the pipeline step
                            # with confidence scores extracted from the result file.
                            if action == "update":
                                step_name = tc_args.get("step", "")
                                step_status = tc_args.get("status", "done")
                                result_file = tc_args.get("result_file")
                                note = tc_args.get("note")
                                confidence = _extract_confidence(
                                    step_name, result_file, workspace,
                                )
                                DbRecorder.record_pipeline_step(
                                    hypothesis_id=hypothesis_id,
                                    agent_id=config.agent_id,
                                    step_name=step_name,
                                    status=step_status,
                                    result_file=result_file,
                                    confidence=confidence,
                                    note=note,
                                    runtime_seconds=round(elapsed, 2),
                                )
                        except Exception:
                            pass  # DB not available
                except (json.JSONDecodeError, TypeError):
                    pass
            elif tc_name in ("spawn_subagent", "check_subagent"):
                try:
                    r = json.loads(result_str)
                    status = r.get("status", "?")
                    aid = r.get("agent_id", "?")
                    if status == "spawned":
                        console.print(f"    [cyan]spawned[/cyan] {aid}")
                        result_summary = f"spawned {aid}"
                        # Auto-create hypothesis when a subagent is spawned.
                        # Agent IDs like "pipeline-MOBOCERTINIB" or "pipeline-erlotinib"
                        # indicate a binding hypothesis.
                        try:
                            from bind_tools.db.recorder import DbRecorder
                            task_text = tc_args.get("task", "")
                            ligand_name = aid.replace("pipeline-", "") if aid.startswith("pipeline-") else aid
                            # Try to extract protein name from task text
                            protein_name = None
                            for token in ("EGFR", "TP53", "BRAF", "HER2", "ALK", "KRAS"):
                                if token in task_text.upper():
                                    protein_name = token
                                    break
                            hypothesis_id = f"{config.run_id}:{ligand_name}"
                            DbRecorder.record_hypothesis(
                                hypothesis_id=hypothesis_id,
                                run_id=config.run_id,
                                agent_id=config.agent_id,
                                protein_name=protein_name,
                                ligand_name=ligand_name,
                                status="running",
                            )
                        except Exception:
                            pass
                    elif status == "running":
                        console.print(f"    [yellow]running[/yellow] {aid}")
                        result_summary = f"running {aid}"
                    elif status in ("completed", "done"):
                        resp = r.get("final_response", "")[:80]
                        console.print(f"    [green]done[/green] {aid} ({r.get('turns', '?')} turns) {resp}")
                        result_summary = f"done {aid}"
                        # Auto-populate pipeline_steps from tool_invocations
                        # when a subagent completes.
                        _backfill_pipeline_steps(
                            config.run_id, aid, workspace,
                        )
                    elif status == "failed":
                        console.print(f"    [red]failed[/red] {aid}: {r.get('error', '')[:100]}")
                        result_summary = f"failed {aid}"
                    else:
                        console.print(f"    [dim]{status}[/dim] {aid}")
                        result_summary = f"{status} {aid}"
                except (json.JSONDecodeError, TypeError):
                    pass

            # Publish tool_result event
            _publish(config.agent_id, "tool_result",
                     turn=turn_num, tool=tc_name,
                     elapsed=round(elapsed, 2), summary=result_summary,
                     resultPreview=result_str[:2000])

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
        _publish(config.agent_id, "done", status="max_turns",
                 turns=config.max_turns, finalResponse=run.final_response)

    run.finished_at = datetime.now(timezone.utc).isoformat()

    # Clean up subagent thread pool.
    executor.shutdown()

    # Backfill pipeline_steps for any subagents that completed but weren't
    # checked via check_subagent (e.g., if the main agent gave its final
    # answer before collecting all subagent results).
    for sub_aid in list(executor._subagent_futures.keys()):
        _backfill_pipeline_steps(config.run_id, sub_aid, workspace)

    # Final sweep: feed any remaining invocations to the tracker and mark
    # hypotheses as completed. Also handles the case where the agent ran
    # batch tools directly without subagents.
    try:
        _feed_new_invocations_to_tracker(hyp_tracker, config.agent_id)
    except Exception:
        pass
    hyp_tracker.finalize()

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
