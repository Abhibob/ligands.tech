"""Recording functions for agent runs, hypotheses, and viz artifacts.

All methods are no-ops if no DB is configured. All methods catch and log
exceptions rather than propagating — the DB should never block tool execution.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from .connection import get_connection, is_db_available
from .schema import migrate

logger = logging.getLogger(__name__)

_schema_applied = False


class DbRecorder:
    """Stateless recorder — every method opens its own connection."""

    @staticmethod
    def ensure_schema() -> None:
        """Create tables if they don't exist. Idempotent, cached after first call."""
        global _schema_applied
        if _schema_applied or not is_db_available():
            return
        try:
            migrate()
            _schema_applied = True
        except Exception as exc:
            logger.warning("Failed to apply DB schema: %s", exc)

    @staticmethod
    def record_agent_start(
        agent_id: str,
        run_id: str,
        parent_agent_id: str | None,
        role: str | None,
        task: str | None,
        model: str,
        workspace_root: str,
    ) -> None:
        """INSERT into agent_runs with status='running'."""
        if not is_db_available():
            return
        try:
            DbRecorder.ensure_schema()
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO agent_runs
                           (agent_id, run_id, parent_agent_id, role, task, model, status, workspace_root)
                           VALUES (%s, %s, %s, %s, %s, %s, 'running', %s)
                           ON CONFLICT (agent_id) DO UPDATE SET status = 'running', started_at = NOW()""",
                        (agent_id, run_id, parent_agent_id, role, task, model, workspace_root),
                    )
        except Exception as exc:
            logger.warning("record_agent_start failed: %s", exc)

    @staticmethod
    def record_agent_finish(
        agent_id: str,
        status: str,
        total_turns: int,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        final_response: str | None,
    ) -> None:
        """UPDATE agent_runs with final state."""
        if not is_db_available():
            return
        try:
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE agent_runs SET
                           status = %s, finished_at = NOW(),
                           total_turns = %s, prompt_tokens = %s,
                           completion_tokens = %s, total_tokens = %s,
                           final_response = %s
                           WHERE agent_id = %s""",
                        (status, total_turns, prompt_tokens, completion_tokens,
                         total_tokens, final_response, agent_id),
                    )
        except Exception as exc:
            logger.warning("record_agent_finish failed: %s", exc)

    @staticmethod
    def record_tool_invocation(
        run_id: str,
        agent_id: str | None,
        request_id: str,
        tool: str,
        subcommand: str | None,
        status: str,
        runtime_seconds: float,
        inputs: dict[str, Any],
        summary: dict[str, Any],
        errors: list[str],
    ) -> None:
        """INSERT into tool_invocations."""
        if not is_db_available():
            return
        try:
            DbRecorder.ensure_schema()
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO tool_invocations
                           (run_id, agent_id, request_id, tool, subcommand,
                            status, runtime_seconds, inputs, summary, errors)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (run_id, agent_id, request_id, tool, subcommand,
                         status, runtime_seconds,
                         json.dumps(inputs, default=str),
                         json.dumps(summary, default=str),
                         json.dumps(errors, default=str)),
                    )
        except Exception as exc:
            logger.warning("record_tool_invocation failed: %s", exc)

    @staticmethod
    def record_viz_artifact(
        run_id: str,
        agent_id: str | None,
        request_id: str | None,
        hypothesis_id: str | None,
        tool: str,
        artifact_type: str,
        file_path: str,
        file_format: str | None = None,
        label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """INSERT into viz_artifacts."""
        if not is_db_available():
            return
        try:
            DbRecorder.ensure_schema()
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO viz_artifacts
                           (run_id, agent_id, request_id, hypothesis_id, tool,
                            artifact_type, file_path, file_format, label, metadata)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (run_id, agent_id, request_id, hypothesis_id, tool,
                         artifact_type, file_path, file_format, label,
                         json.dumps(metadata or {}, default=str)),
                    )
        except Exception as exc:
            logger.warning("record_viz_artifact failed: %s", exc)

    @staticmethod
    def record_hypothesis(
        hypothesis_id: str,
        run_id: str,
        agent_id: str | None,
        protein_name: str | None = None,
        ligand_name: str | None = None,
        status: str = "pending",
    ) -> None:
        """INSERT into hypotheses. On conflict, update status and timestamp."""
        if not is_db_available():
            return
        try:
            DbRecorder.ensure_schema()
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO hypotheses
                           (id, run_id, agent_id, protein_name, ligand_name, status)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           ON CONFLICT (id) DO UPDATE SET
                             status = EXCLUDED.status,
                             updated_at = NOW()""",
                        (hypothesis_id, run_id, agent_id, protein_name, ligand_name, status),
                    )
        except Exception as exc:
            logger.warning("record_hypothesis failed: %s", exc)

    @staticmethod
    def record_pipeline_step(
        hypothesis_id: str,
        agent_id: str | None,
        step_name: str,
        status: str,
        result_file: str | None = None,
        request_id: str | None = None,
        confidence: dict[str, Any] | None = None,
        note: str | None = None,
        runtime_seconds: float | None = None,
    ) -> None:
        """INSERT into pipeline_steps."""
        if not is_db_available():
            return
        try:
            DbRecorder.ensure_schema()
            with get_connection() as conn:
                if conn is None:
                    return
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO pipeline_steps
                           (hypothesis_id, agent_id, step_name, status,
                            result_file, request_id, confidence, note,
                            runtime_seconds, finished_at)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())""",
                        (hypothesis_id, agent_id, step_name, status,
                         result_file, request_id,
                         json.dumps(confidence, default=str) if confidence else None,
                         note, runtime_seconds),
                    )
        except Exception as exc:
            logger.warning("record_pipeline_step failed: %s", exc)
