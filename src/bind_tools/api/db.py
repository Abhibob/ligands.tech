"""Read-only query layer for the API server.

Uses the same get_connection() + RealDictCursor pattern as DbRecorder,
but only does SELECTs.
"""

from __future__ import annotations

import logging

from bind_tools.db.connection import get_connection

logger = logging.getLogger(__name__)


def _query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a SELECT and return list of row dicts."""
    with get_connection() as conn:
        if conn is None:
            return []
        import psycopg2.extras

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def _query_one(sql: str, params: tuple = ()) -> dict | None:
    """Execute a SELECT and return a single row dict, or None."""
    rows = _query(sql, params)
    return rows[0] if rows else None


# ── Agent runs ──────────────────────────────────────────────────────


def list_agents(
    limit: int = 50,
    offset: int = 0,
    parent_only: bool = True,
    status: str | None = None,
) -> list[dict]:
    """Top-level agents with child_count subquery. ORDER BY created_at DESC."""
    filters = []
    params: list = []
    if parent_only:
        filters.append("parent_agent_id IS NULL")
    if status == "running":
        filters.append("status = 'running'")
    elif status == "finished":
        filters.append("status IN ('completed', 'failed', 'max_turns')")
    elif status:
        filters.append("status = %s")
        params.append(status)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    params.extend([limit, offset])
    sql = f"""
        SELECT a.*,
               (SELECT COUNT(*) FROM agent_runs c WHERE c.parent_agent_id = a.agent_id) AS child_count
        FROM agent_runs a
        {where}
        ORDER BY a.created_at DESC
        LIMIT %s OFFSET %s
    """
    return _query(sql, tuple(params))


def get_agent(agent_id: str) -> dict | None:
    """Single agent_run by PK."""
    sql = """
        SELECT a.*,
               (SELECT COUNT(*) FROM agent_runs c WHERE c.parent_agent_id = a.agent_id) AS child_count
        FROM agent_runs a
        WHERE a.agent_id = %s
    """
    return _query_one(sql, (agent_id,))


def get_agent_children(agent_id: str) -> list[dict]:
    """Child agents WHERE parent_agent_id = agent_id."""
    sql = """
        SELECT a.*,
               (SELECT COUNT(*) FROM agent_runs c WHERE c.parent_agent_id = a.agent_id) AS child_count
        FROM agent_runs a
        WHERE a.parent_agent_id = %s
        ORDER BY a.created_at ASC
    """
    return _query(sql, (agent_id,))


# ── Hypotheses + pipeline steps ─────────────────────────────────────


def get_agent_hypotheses(agent_id: str) -> list[dict]:
    """Hypotheses for an agent, each with nested pipeline_steps list."""
    hyps = _query(
        "SELECT * FROM hypotheses WHERE agent_id = %s ORDER BY created_at ASC",
        (agent_id,),
    )
    for h in hyps:
        h["steps"] = _query(
            "SELECT * FROM pipeline_steps WHERE hypothesis_id = %s ORDER BY id ASC",
            (h["id"],),
        )
    return hyps


def get_hypothesis(hypothesis_id: str) -> dict | None:
    """Single hypothesis with nested steps."""
    h = _query_one("SELECT * FROM hypotheses WHERE id = %s", (hypothesis_id,))
    if h:
        h["steps"] = _query(
            "SELECT * FROM pipeline_steps WHERE hypothesis_id = %s ORDER BY id ASC",
            (hypothesis_id,),
        )
    return h


# ── Artifacts ───────────────────────────────────────────────────────


def get_agent_artifacts(agent_id: str) -> list[dict]:
    """viz_artifacts WHERE agent_id = %s."""
    return _query(
        "SELECT * FROM viz_artifacts WHERE agent_id = %s ORDER BY created_at ASC",
        (agent_id,),
    )


# ── Tool invocations ───────────────────────────────────────────────


def get_agent_invocations(agent_id: str) -> list[dict]:
    """tool_invocations WHERE agent_id = %s ORDER BY created_at."""
    return _query(
        "SELECT * FROM tool_invocations WHERE agent_id = %s ORDER BY created_at ASC",
        (agent_id,),
    )


# ── Run status (for polling) ───────────────────────────────────────


def get_run_status(run_id: str) -> dict | None:
    """agent_runs WHERE run_id = %s — for polling after POST /api/runs."""
    return _query_one(
        """SELECT agent_id, run_id, status, total_turns, final_response,
                  started_at, finished_at
           FROM agent_runs WHERE run_id = %s AND parent_agent_id IS NULL""",
        (run_id,),
    )


# ── Aggregate stats ────────────────────────────────────────────────


def get_stats() -> dict:
    """Aggregate stats for the home page."""
    row = _query_one("""
        SELECT
            (SELECT COUNT(*) FROM agent_runs WHERE parent_agent_id IS NULL) AS agent_count,
            (SELECT COUNT(*) FROM hypotheses) AS hypothesis_count,
            (SELECT COUNT(DISTINCT protein_name) FROM hypotheses WHERE protein_name IS NOT NULL) AS protein_count,
            (SELECT COUNT(DISTINCT ligand_name) FROM hypotheses WHERE ligand_name IS NOT NULL) AS ligand_count
    """)
    return row or {"agent_count": 0, "hypothesis_count": 0, "protein_count": 0, "ligand_count": 0}
