"""OpenAI SDK client factory for Modal and OpenRouter backends."""

from __future__ import annotations

from openai import OpenAI

from .config import AgentConfig


def make_client(config: AgentConfig) -> OpenAI:
    """Create an OpenAI client configured for the agent's LLM endpoint."""
    return OpenAI(
        api_key=config.api_key or "no-key",
        base_url=config.base_url,
        default_headers={
            "HTTP-Referer": "https://bindingops.dev",
            "X-Title": "BindingOps Agent",
        },
    )
