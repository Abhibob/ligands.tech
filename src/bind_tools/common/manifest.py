"""Markdown manifest writer for batch CLI operations."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def write_manifest(
    path: Path,
    title: str,
    columns: list[str],
    rows: list[list[str]],
    metadata: dict[str, str],
    summary_lines: list[str] | None = None,
    failed_items: list[dict[str, str]] | None = None,
) -> Path:
    """Write a Markdown manifest file with a sorted results table.

    The caller is responsible for pre-sorting rows (best-first).
    The first ~3KB always contains the header + top ~20 rows, ensuring
    readability within the agent's 12KB read_file limit.

    Returns the path written.
    """
    lines: list[str] = []
    lines.append(f"# {title}")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).isoformat()}")
    for key, value in metadata.items():
        lines.append(f"**{key}:** {value}")
    lines.append("")

    # Markdown table
    lines.append("## Results")
    lines.append("")
    lines.append("| " + " | ".join(columns) + " |")
    lines.append("| " + " | ".join("---" for _ in columns) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(c) for c in row) + " |")
    lines.append("")

    if summary_lines:
        lines.append("## Summary")
        for s in summary_lines:
            lines.append(f"- {s}")
        lines.append("")

    if failed_items:
        lines.append("## Failed")
        for item in failed_items:
            lines.append(f"- {item.get('id', '?')}: {item.get('error', 'unknown')}")
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
    return path
