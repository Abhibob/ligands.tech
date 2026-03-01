"""Agent configuration loaded from environment variables and CLI flags."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timezone

from pydantic import BaseModel, Field


def _default_run_id() -> str:
    now = datetime.now(timezone.utc)
    hex_suffix = secrets.token_hex(3)
    return f"run-{now:%Y%m%d-%H%M%S}-{hex_suffix}"


def _default_agent_id() -> str:
    return f"agent-{secrets.token_hex(6)}"


def _default_spec_root() -> str:
    """Derive the project root from the package location.

    Walk up from src/bind_tools/agent/config.py to find the directory
    containing pyproject.toml. Falls back to cwd.
    """
    from pathlib import Path

    anchor = Path(__file__).resolve().parent  # agent/
    for parent in (anchor, *anchor.parents):
        if (parent / "pyproject.toml").is_file():
            return str(parent)
    return "."


class AgentConfig(BaseModel):
    """Runtime configuration for the agent harness."""

    api_key: str = ""
    base_url: str = "https://benwu408--gpt-oss-120b-serve.modal.run/v1"
    model: str = "openai/gpt-oss-120b"
    workspace_root: str = "./workspace"
    run_id: str = Field(default_factory=_default_run_id)
    agent_id: str = Field(default_factory=_default_agent_id)
    parent_agent_id: str | None = None
    db_url: str | None = None
    max_turns: int = 500
    command_timeout_s: int = 600
    spec_root: str = Field(default_factory=_default_spec_root)
    stream: bool = True
    verbose: bool = False

    # Command stdout/stderr is truncated — just confirmation ("did it work?").
    # The real data lives in --json-out files read via read_file.
    max_cmd_output_chars: int = 1_500
    # read_file rejects files larger than this (PDB, SDF, CIF are too large).
    max_read_chars: int = 12_000

    @classmethod
    def from_env(cls, **overrides: object) -> AgentConfig:
        """Load config from environment variables, then apply CLI overrides."""
        env_vals: dict[str, object] = {}

        # API key: BIND_AGENT_API_KEY > OPENROUTER_API_KEY
        api_key = os.environ.get("BIND_AGENT_API_KEY") or os.environ.get(
            "OPENROUTER_API_KEY", ""
        )
        if api_key:
            env_vals["api_key"] = api_key

        base_url = os.environ.get("BIND_AGENT_BASE_URL")
        if base_url:
            env_vals["base_url"] = base_url

        # Model: BIND_AGENT_MODEL > BIND_TOOLS_MODEL
        model = os.environ.get("BIND_AGENT_MODEL") or os.environ.get("BIND_TOOLS_MODEL")
        if model:
            env_vals["model"] = model

        workspace = os.environ.get("BIND_TOOLS_WORKSPACE")
        if workspace:
            env_vals["workspace_root"] = workspace

        # Agent identity
        agent_id = os.environ.get("BIND_AGENT_ID")
        if agent_id:
            env_vals["agent_id"] = agent_id

        parent_agent_id = os.environ.get("BIND_PARENT_AGENT_ID")
        if parent_agent_id:
            env_vals["parent_agent_id"] = parent_agent_id

        # Spec root (project root for skill files and venv)
        spec_root = os.environ.get("BIND_SPEC_ROOT")
        if spec_root:
            env_vals["spec_root"] = spec_root

        # Database
        db_url = os.environ.get("BIND_DB_URL") or os.environ.get("DATABASE_URL")
        if db_url:
            env_vals["db_url"] = db_url

        # Merge: env values first, then CLI overrides win
        merged = {**env_vals, **{k: v for k, v in overrides.items() if v is not None}}
        return cls(**merged)
