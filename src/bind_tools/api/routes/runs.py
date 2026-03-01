"""Agent launcher: POST /api/runs to spawn an agent, GET to poll status."""

from __future__ import annotations

import logging
import threading

from fastapi import APIRouter, HTTPException

from bind_tools.api import db
from bind_tools.api.models import RunCreateRequest, RunCreateResponse, RunStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["runs"])


def _run_agent_thread(prompt: str, run_id: str, agent_id: str) -> None:
    """Run the agent loop in a daemon thread."""
    try:
        from openai import OpenAI

        from bind_tools.agent.config import AgentConfig
        from bind_tools.agent.loop import run_agent
        from bind_tools.agent.workspace import Workspace

        config = AgentConfig.from_env(run_id=run_id, agent_id=agent_id)
        workspace = Workspace.create(config)
        client = OpenAI(
            api_key=config.api_key or "no-key",
            base_url=config.base_url,
            default_headers={
                "HTTP-Referer": "https://bindingops.dev",
                "X-Title": "BindingOps Agent",
            },
        )
        run_agent(prompt, config=config, workspace=workspace, client=client)
    except Exception:
        logger.exception("Agent thread failed for run_id=%s", run_id)


@router.post("/runs", response_model=RunCreateResponse, status_code=201)
def create_run(req: RunCreateRequest):
    from bind_tools.agent.config import AgentConfig

    config = AgentConfig.from_env()
    run_id = config.run_id
    agent_id = config.agent_id

    t = threading.Thread(
        target=_run_agent_thread,
        args=(req.prompt, run_id, agent_id),
        daemon=True,
        name=f"agent-{run_id}",
    )
    t.start()

    return RunCreateResponse(run_id=run_id, agent_id=agent_id)


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str):
    row = db.get_run_status(run_id)
    if not row:
        raise HTTPException(404, detail="Run not found")
    return RunStatusResponse(**row)
