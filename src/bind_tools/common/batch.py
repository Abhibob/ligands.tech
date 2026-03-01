"""Batch processing helpers for directory-based CLI input."""

from __future__ import annotations

from pathlib import Path

from .errors import InputMissingError


def glob_input_dir(
    dir_path: str | Path,
    extensions: tuple[str, ...],
    label: str = "input directory",
) -> list[Path]:
    """Glob a directory for files matching the given extensions.

    Returns an alphabetically sorted, deduplicated list of matching paths.
    Raises InputMissingError if the directory doesn't exist or no files match.
    """
    d = Path(dir_path)
    if not d.is_dir():
        raise InputMissingError(f"{label} does not exist or is not a directory: {d}")

    files: list[Path] = []
    for ext in extensions:
        files.extend(d.glob(f"*{ext}"))
    files = sorted(set(files))

    if not files:
        raise InputMissingError(
            f"No files matching {extensions} found in {label}: {d}"
        )
    return files
