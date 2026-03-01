"""Read endpoints for agents, hypotheses, artifacts, and invocations."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from bind_tools.api import db
from bind_tools.api.models import (
    AgentRunResponse,
    HypothesisResponse,
    StatsResponse,
    ToolInvocationResponse,
    VizArtifactResponse,
)

router = APIRouter(prefix="/api", tags=["agents"])


@router.get("/agents", response_model=List[AgentRunResponse])
def list_agents(limit: int = 50, offset: int = 0, status: Optional[str] = None):
    rows = db.list_agents(limit=limit, offset=offset, parent_only=True, status=status)
    return [AgentRunResponse(**r) for r in rows]


@router.get("/agents/{agent_id}", response_model=AgentRunResponse)
def get_agent(agent_id: str):
    row = db.get_agent(agent_id)
    if not row:
        raise HTTPException(404, detail="Agent not found")
    return AgentRunResponse(**row)


@router.get("/agents/{agent_id}/children", response_model=List[AgentRunResponse])
def get_agent_children(agent_id: str):
    rows = db.get_agent_children(agent_id)
    return [AgentRunResponse(**r) for r in rows]


@router.get("/agents/{agent_id}/hypotheses", response_model=List[HypothesisResponse])
def get_agent_hypotheses(agent_id: str):
    rows = db.get_agent_hypotheses(agent_id)
    return [HypothesisResponse(**r) for r in rows]


@router.get("/agents/{agent_id}/artifacts", response_model=List[VizArtifactResponse])
def get_agent_artifacts(agent_id: str):
    rows = db.get_agent_artifacts(agent_id)
    return [VizArtifactResponse(**r) for r in rows]


@router.get("/agents/{agent_id}/invocations", response_model=List[ToolInvocationResponse])
def get_agent_invocations(agent_id: str):
    rows = db.get_agent_invocations(agent_id)
    return [ToolInvocationResponse(**r) for r in rows]


@router.get("/hypotheses/{hypothesis_id}", response_model=HypothesisResponse)
def get_hypothesis(hypothesis_id: str):
    row = db.get_hypothesis(hypothesis_id)
    if not row:
        raise HTTPException(404, detail="Hypothesis not found")
    return HypothesisResponse(**row)


@router.get("/stats", response_model=StatsResponse)
def get_stats():
    return StatsResponse(**db.get_stats())
