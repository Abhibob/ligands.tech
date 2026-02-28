"""QMD runner: keyword/glob search over local Markdown, JSON, YAML files."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

import yaml

from .models import QmdSearchHit


# Kind to file pattern mapping
KIND_PATTERNS: dict[str, list[str]] = {
    "skill": ["**/SKILL.md", "**/skills/**/*.md"],
    "spec": ["**/specs/**/*.md"],
    "schema": ["**/schemas/**/*.json"],
    "example": ["**/examples/**/*.*"],
    "note": ["**/docs/**/*.md", "**/AGENTS.md", "**/README.md"],
    "any": ["**/*.md", "**/*.json", "**/*.yaml", "**/*.yml"],
}


def _load_collections(root: Path) -> dict[str, dict]:
    """Load collection definitions from examples/qmd/collections.yaml if present."""
    candidates = [
        root / "examples" / "qmd" / "collections.yaml",
        root / "collections.yaml",
    ]
    for c in candidates:
        if c.is_file():
            data = yaml.safe_load(c.read_text())
            if data and "collections" in data:
                return {col["name"]: col for col in data["collections"]}
    return {}


def _gather_files(root: Path, kind: str, collections: list[str] | None = None) -> list[Path]:
    """Gather candidate files by kind and optional collection filters."""
    all_collections = _load_collections(root)

    # If specific collections requested, use their include patterns
    if collections:
        patterns: list[str] = []
        for cname in collections:
            col = all_collections.get(cname)
            if col and "include" in col:
                patterns.extend(col["include"])
        if not patterns:
            patterns = KIND_PATTERNS.get(kind, KIND_PATTERNS["any"])
    else:
        patterns = KIND_PATTERNS.get(kind, KIND_PATTERNS["any"])

    files: set[Path] = set()
    for pattern in patterns:
        for match in root.rglob(pattern.lstrip("*").lstrip("/")):
            if match.is_file() and ".git" not in match.parts:
                files.add(match)

    return sorted(files)


def _score_file(path: Path, terms: list[str], root: Path) -> tuple[float, str, int, int]:
    """Score a file against search terms. Returns (score, snippet, line_start, line_end)."""
    try:
        content = path.read_text(errors="replace")
    except Exception:
        return 0.0, "", 0, 0

    content_lower = content.lower()
    rel_path = str(path.relative_to(root)).lower()
    lines = content.split("\n")

    score = 0.0
    best_line = 0
    best_snippet = ""

    for term in terms:
        term_lower = term.lower()
        # Filename match is worth more
        if term_lower in rel_path:
            score += 10.0
        # Count content matches
        count = content_lower.count(term_lower)
        score += min(count, 10)  # cap per-term contribution

        # Find best matching line for snippet
        if not best_snippet:
            for i, line in enumerate(lines):
                if term_lower in line.lower():
                    best_line = i + 1
                    # Get a few lines of context
                    start = max(0, i - 1)
                    end = min(len(lines), i + 3)
                    best_snippet = "\n".join(lines[start:end])
                    break

    return score, best_snippet, best_line, min(best_line + 3, len(lines))


def _infer_title(path: Path) -> str:
    """Extract a title from the file (first heading or filename)."""
    try:
        for line in path.open(errors="replace"):
            line = line.strip()
            if line.startswith("# "):
                return line[2:].strip()
            if line.startswith("---"):
                continue
            if line.startswith("name:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return path.stem


def _infer_kind(path: Path) -> str:
    """Infer the kind from the file path."""
    parts = path.parts
    if "skills" in parts or path.name == "SKILL.md":
        return "skill"
    if "specs" in parts:
        return "spec"
    if "schemas" in parts:
        return "schema"
    if "examples" in parts:
        return "example"
    if "docs" in parts:
        return "note"
    return "any"


def search(
    root: Path,
    text: str,
    *,
    kind: str = "any",
    top_k: int = 5,
    collections: list[str] | None = None,
    must_include: list[str] | None = None,
    must_exclude: list[str] | None = None,
) -> list[QmdSearchHit]:
    """Run a keyword search over local files."""
    root = root.resolve()
    files = _gather_files(root, kind, collections)

    # Apply must_include / must_exclude glob filters
    if must_include:
        files = [f for f in files if any(fnmatch.fnmatch(str(f), pat) for pat in must_include)]
    if must_exclude:
        files = [f for f in files if not any(fnmatch.fnmatch(str(f), pat) for pat in must_exclude)]

    # Tokenize search text
    terms = [t for t in re.split(r"\s+", text.strip()) if len(t) >= 2]
    if not terms:
        return []

    scored: list[tuple[float, Path, str, int, int]] = []
    for f in files:
        score, snippet, line_start, line_end = _score_file(f, terms, root)
        if score > 0:
            scored.append((score, f, snippet, line_start, line_end))

    scored.sort(key=lambda x: x[0], reverse=True)

    results: list[QmdSearchHit] = []
    for score, path, snippet, line_start, line_end in scored[:top_k]:
        results.append(
            QmdSearchHit(
                path=str(path.relative_to(root)),
                title=_infer_title(path),
                kind=_infer_kind(path),
                score=round(score, 2),
                snippet=snippet[:500],
                lineStart=line_start,
                lineEnd=line_end,
            )
        )

    return results
