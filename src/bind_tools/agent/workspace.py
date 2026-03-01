"""Workspace directory creation and path resolution."""

from __future__ import annotations

from pathlib import Path

from .config import AgentConfig

# Subdirectories created for every run.
_SUBDIRS = (
    "proteins",
    "ligands",
    "boltz",
    "docking",
    "validation",
    "interactions",
    "requests",
    "results",
)


class Workspace:
    """Manages a per-run workspace directory tree."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @classmethod
    def create(cls, config: AgentConfig) -> Workspace:
        """Create the workspace directory structure and return a Workspace."""
        root = Path(config.workspace_root).resolve() / config.run_id
        for subdir in _SUBDIRS:
            (root / subdir).mkdir(parents=True, exist_ok=True)
        return cls(root)

    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path string against the workspace root.

        Absolute paths are returned as-is; relative paths are resolved
        against ``self.root``.
        """
        p = Path(path_str)
        if p.is_absolute():
            return p
        return (self.root / p).resolve()

    def layout_description(self) -> str:
        """Return a text description of the workspace for the system prompt."""
        return (
            "# Workspace\n\n"
            f"Your workspace is: `{self.root}`\n\n"
            "**All commands you run via the `command` tool use this directory as "
            "their working directory.** Use relative paths — they resolve against "
            "the workspace root automatically.\n\n"
            "The following directories are pre-created and ready to use:\n\n"
            "| Directory | Use for | CLI flag pattern |\n"
            "|-----------|---------|------------------|\n"
            "| `proteins/` | FASTA, PDB, CIF files | `--download-dir proteins/` |\n"
            "| `ligands/` | SDF files | `--download-dir ligands/` |\n"
            "| `boltz/` | Boltz-2 prediction outputs | `--artifacts-dir boltz/` |\n"
            "| `docking/` | gnina docking outputs | `--artifacts-dir docking/` |\n"
            "| `validation/` | PoseBusters results | `--artifacts-dir validation/` |\n"
            "| `interactions/` | PLIP interaction profiles | `--artifacts-dir interactions/` |\n"
            "| `requests/` | YAML/JSON request files you generate | `--request requests/my.yaml` |\n"
            "| `results/` | JSON result envelopes | `--json-out results/name.json` |\n\n"
            "## Workflow pattern\n\n"
            "1. Run a command with `--json-out results/something.json`\n"
            "2. Use `read_file` to read `results/something.json`\n"
            "3. Extract the file paths you need (e.g. `summary.fasta_path`, "
            "`summary.sdf_path`, `artifacts.primaryComplexPath`)\n"
            "4. Pass those paths to the next command\n\n"
            "Use `list_files` to discover what files a command produced "
            "(e.g. `list_files(path=\"boltz/\")`).\n"
            "Use `write_file` to create request YAML files or any other files — "
            "parent directories are created automatically.\n\n"
            "**Do not read large binary files** (PDB, CIF, SDF). Just pass their "
            "paths to the next command."
        )
