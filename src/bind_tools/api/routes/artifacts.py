"""File serving for PDB/SDF/CIF artifacts from workspaces."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api", tags=["artifacts"])

# Workspace root — artifacts are served relative to this
_WORKSPACE_ROOT = Path(os.environ.get("BIND_TOOLS_WORKSPACE", "./workspace")).resolve()

_MIME_MAP = {
    ".pdb": "chemical/x-pdb",
    ".cif": "chemical/x-cif",
    ".sdf": "chemical/x-mdl-sdfile",
    ".mol2": "chemical/x-mol2",
    ".json": "application/json",
    ".yaml": "application/x-yaml",
    ".yml": "application/x-yaml",
    ".csv": "text/csv",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


@router.get("/artifacts/{path:path}")
def serve_artifact(path: str):
    resolved = (_WORKSPACE_ROOT / path).resolve()

    # Path-traversal protection: must be under workspace root
    if not str(resolved).startswith(str(_WORKSPACE_ROOT)):
        raise HTTPException(403, detail="Access denied")

    if not resolved.is_file():
        raise HTTPException(404, detail="File not found")

    media_type = _MIME_MAP.get(resolved.suffix.lower(), "application/octet-stream")
    return FileResponse(resolved, media_type=media_type, filename=resolved.name)
