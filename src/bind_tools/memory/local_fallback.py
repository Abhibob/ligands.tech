"""Local filesystem fallback when no Supermemory API key is set.

Stores memories as Markdown files with YAML front-matter in
<workspace>/memory/<tag>/findings/.  Provides keyword search (not semantic).
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .models import MemoryAddSpec, MemoryProfileSpec, MemorySearchSpec

_WORKSPACE = os.environ.get("BIND_TOOLS_WORKSPACE", ".")


def _memory_root() -> Path:
    ws = os.environ.get("BIND_TOOLS_WORKSPACE", _WORKSPACE)
    return Path(ws) / "memory"


class LocalMemoryClient:
    """File-based memory backend — same interface as SupermemoryClient."""

    # ── add ───────────────────────────────────────────────────────────

    def add(self, spec: MemoryAddSpec) -> dict[str, Any]:
        tag_dir = _memory_root() / spec.container_tag / "findings"
        tag_dir.mkdir(parents=True, exist_ok=True)

        doc_id = spec.custom_id or uuid4().hex[:12]
        safe_id = re.sub(r"[^\w\-]", "_", doc_id)
        path = tag_dir / f"{safe_id}.md"

        # Build front-matter.
        front: dict[str, Any] = {
            "id": doc_id,
            "tag": spec.container_tag,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        if spec.metadata:
            front["metadata"] = spec.metadata

        fm_lines = ["---"]
        fm_lines.append(json.dumps(front, indent=2))
        fm_lines.append("---")
        fm_lines.append("")
        fm_lines.append(spec.content)

        path.write_text("\n".join(fm_lines))
        return {"id": doc_id, "path": str(path), "backend": "local"}

    # ── search ────────────────────────────────────────────────────────

    def search(self, spec: MemorySearchSpec) -> dict[str, Any]:
        results: list[dict[str, Any]] = []
        query_lower = spec.query.lower()
        keywords = query_lower.split()

        # Determine which tag directories to search.
        root = _memory_root()
        if spec.container_tag:
            tag_dirs = [root / spec.container_tag / "findings"]
        else:
            tag_dirs = list(root.glob("*/findings"))

        for tag_dir in tag_dirs:
            if not tag_dir.is_dir():
                continue
            for md_file in tag_dir.glob("*.md"):
                text = md_file.read_text(errors="replace")
                text_lower = text.lower()
                # Simple keyword matching — any keyword matches.
                score = sum(1 for kw in keywords if kw in text_lower)
                if score > 0:
                    # Extract content (after second ---).
                    parts = text.split("---", 2)
                    content = parts[2].strip() if len(parts) >= 3 else text
                    results.append({
                        "id": md_file.stem,
                        "content": content[:2000],
                        "score": score / len(keywords) if keywords else 0,
                        "path": str(md_file),
                    })

        # Sort by score descending, limit.
        results.sort(key=lambda r: r["score"], reverse=True)
        results = results[: spec.limit]

        return {"results": results, "total": len(results), "backend": "local"}

    # ── profile ───────────────────────────────────────────────────────

    def profile(self, spec: MemoryProfileSpec) -> dict[str, Any]:
        tag_dir = _memory_root() / spec.container_tag / "findings"
        if not tag_dir.is_dir():
            return {"profile": "No memories found for this tag.", "backend": "local"}

        files = sorted(tag_dir.glob("*.md"))
        snippets: list[str] = []
        for f in files[:20]:
            text = f.read_text(errors="replace")
            parts = text.split("---", 2)
            content = parts[2].strip() if len(parts) >= 3 else text
            snippets.append(f"## {f.stem}\n{content[:500]}")

        profile_text = "\n\n".join(snippets) if snippets else "No memories found."
        return {
            "profile": profile_text,
            "num_documents": len(files),
            "backend": "local",
        }

    # ── doctor ────────────────────────────────────────────────────────

    def check_connectivity(self) -> dict[str, Any]:
        root = _memory_root()
        return {
            "status": "ok",
            "backend": "local",
            "memory_dir": str(root),
        }
