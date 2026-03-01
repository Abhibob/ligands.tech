"""Tag and metadata conventions for Supermemory entries."""

from __future__ import annotations


def run_tag(run_id: str) -> str:
    """Container tag for a specific run."""
    return f"run-{run_id}" if not run_id.startswith("run-") else run_id


# Standard metadata keys.
TOOL_KEY = "tool"           # "boltz", "gnina", etc.
STAGE_KEY = "stage"         # "resolve", "predict", "dock", "validate"
TARGET_KEY = "target"       # protein name
LIGAND_KEY = "ligand_id"
AGENT_KEY = "agent_id"

# Entity context strings for Supermemory extraction hints.
ENTITY_CONTEXTS: dict[str, str] = {
    "boltz": "Boltz-2 result. Extract: binder probability, affinity, confidence, pose path.",
    "gnina": "gnina result. Extract: CNN score, affinity, energy, receptor, ligand.",
    "posebusters": "PoseBusters result. Extract: pass/fail, failures.",
    "plip": "PLIP result. Extract: interaction counts, key residues.",
    "resolve": "Resolution result. Extract: protein name, PDB/FASTA/SDF paths.",
}
