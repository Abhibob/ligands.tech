"""Pydantic models for tracking agent runs."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A single tool invocation within a turn."""

    id: str = ""
    name: str = ""
    arguments: str = ""
    result: str = ""
    elapsed_s: float = 0.0


class Turn(BaseModel):
    """One assistant turn (LLM response + tool calls)."""

    turn_number: int = 0
    assistant_content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: str = ""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class AgentRun(BaseModel):
    """Full record of an agent run for debugging and replay."""

    run_id: str = ""
    agent_id: str = ""
    parent_agent_id: str = ""
    workspace_root: str = ""
    model: str = ""
    started_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    finished_at: str = ""
    turns: list[Turn] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    final_response: str = ""
    status: str = "running"  # running | completed | max_turns | error
