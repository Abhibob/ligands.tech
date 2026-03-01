"""Database schema — idempotent CREATE TABLE IF NOT EXISTS statements."""

from __future__ import annotations

import logging

from .connection import get_connection

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
-- Agent hierarchy: tracks parent/child agent relationships
CREATE TABLE IF NOT EXISTS agent_runs (
    agent_id          TEXT PRIMARY KEY,
    run_id            TEXT NOT NULL,
    parent_agent_id   TEXT REFERENCES agent_runs(agent_id),
    role              TEXT,
    task              TEXT,
    model             TEXT,
    status            TEXT NOT NULL DEFAULT 'pending',
    workspace_root    TEXT,
    started_at        TIMESTAMPTZ DEFAULT NOW(),
    finished_at       TIMESTAMPTZ,
    total_turns       INTEGER DEFAULT 0,
    prompt_tokens     INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens      INTEGER DEFAULT 0,
    final_response    TEXT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_agent_runs_run_id ON agent_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_parent ON agent_runs(parent_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);

-- Binding hypotheses being processed by each agent
CREATE TABLE IF NOT EXISTS hypotheses (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT REFERENCES agent_runs(agent_id),
    protein_name    TEXT,
    ligand_name     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_hypotheses_run_id ON hypotheses(run_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_agent_id ON hypotheses(agent_id);

-- Per-hypothesis pipeline step outcomes with confidence scores
CREATE TABLE IF NOT EXISTS pipeline_steps (
    id              SERIAL PRIMARY KEY,
    hypothesis_id   TEXT NOT NULL REFERENCES hypotheses(id),
    agent_id        TEXT REFERENCES agent_runs(agent_id),
    step_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'pending',
    result_file     TEXT,
    request_id      TEXT,
    confidence      JSONB,
    note            TEXT,
    started_at      TIMESTAMPTZ,
    finished_at     TIMESTAMPTZ,
    runtime_seconds FLOAT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_hypothesis ON pipeline_steps(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_steps_agent ON pipeline_steps(agent_id);

-- Visualization artifacts: files tagged with agent_id + confidence metadata
CREATE TABLE IF NOT EXISTS viz_artifacts (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT,
    request_id      TEXT,
    hypothesis_id   TEXT REFERENCES hypotheses(id),
    tool            TEXT NOT NULL,
    artifact_type   TEXT NOT NULL,
    file_path       TEXT NOT NULL,
    file_format     TEXT,
    label           TEXT,
    metadata        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_viz_artifacts_run_id ON viz_artifacts(run_id);
CREATE INDEX IF NOT EXISTS idx_viz_artifacts_agent_id ON viz_artifacts(agent_id);
CREATE INDEX IF NOT EXISTS idx_viz_artifacts_tool ON viz_artifacts(tool);
CREATE INDEX IF NOT EXISTS idx_viz_artifacts_type ON viz_artifacts(artifact_type);
CREATE INDEX IF NOT EXISTS idx_viz_artifacts_hypothesis ON viz_artifacts(hypothesis_id);

-- Every CLI tool invocation with outcome
CREATE TABLE IF NOT EXISTS tool_invocations (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT NOT NULL,
    agent_id        TEXT,
    request_id      TEXT,
    tool            TEXT NOT NULL,
    subcommand      TEXT,
    status          TEXT NOT NULL,
    runtime_seconds FLOAT,
    inputs          JSONB DEFAULT '{}',
    summary         JSONB DEFAULT '{}',
    errors          JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_run_id ON tool_invocations(run_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_agent_id ON tool_invocations(agent_id);
"""


def migrate() -> None:
    """Apply schema to the database. Idempotent — safe to call repeatedly."""
    with get_connection() as conn:
        if conn is None:
            return
        with conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)
        logger.debug("Database schema applied successfully")
