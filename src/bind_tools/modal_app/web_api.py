"""HTTP REST API for Boltz & GNINA on Modal.

Provides JSON-based endpoints that dispatch GPU work to the existing
BoltzPredictor (A100) and GninaRunner (T4) containers via .remote().
"""

from __future__ import annotations

import base64
import os
from typing import Any

import modal
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from ._base import app

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FileB64(BaseModel):
    """A file encoded as base64 for JSON transport."""

    name: str = Field(..., description="Filename (e.g. 'protein.pdb')")
    data: str = Field(..., description="Base64-encoded file contents")

    def to_bytes_dict(self) -> dict[str, str | bytes]:
        return {"name": self.name, "data": base64.b64decode(self.data)}


class BoltzPredictRequest(BaseModel):
    """Request body for POST /v1/boltz/predict."""

    upstream_yaml: dict[str, Any] = Field(
        ..., description="Boltz input YAML dict (translate_to_upstream_yaml output)"
    )
    input_files: list[FileB64] = Field(
        default_factory=list,
        description="Referenced input files (FASTA, SDF, etc.) as base64",
    )
    accelerator: str = Field("gpu", description="'gpu' or 'cpu'")
    use_msa_server: bool = False
    recycling_steps: int | None = None
    diffusion_samples: int | None = None
    seed: int | None = None


class BoltzFileOut(BaseModel):
    """An output file from Boltz, base64-encoded."""

    name: str
    data: str  # base64


class BoltzPredictResponse(BaseModel):
    """Response body for POST /v1/boltz/predict."""

    returncode: int
    stdout: str
    stderr: str
    output_files: list[BoltzFileOut] = []
    confidence: dict[str, Any] | None = None
    affinity: dict[str, Any] | None = None
    primary_complex_path: str | None = None
    structure_filenames: list[str] = []


class GninaRequest(BaseModel):
    """Request body for POST /v1/gnina/{dock,score,minimize}."""

    gnina_args: list[str] = Field(
        ..., description="Pre-built gnina CLI args (filenames, not full paths)"
    )
    input_files: list[FileB64] = Field(
        ..., description="Receptor PDB, ligand SDF, etc. as base64"
    )
    output_filename: str | None = Field(
        None, description="Expected output SDF filename (None for score mode)"
    )


class GninaFileOut(BaseModel):
    """An output file from GNINA, base64-encoded."""

    name: str
    data: str  # base64


class GninaResponse(BaseModel):
    """Response body for GNINA endpoints."""

    returncode: int
    stdout: str
    stderr: str
    output_file: GninaFileOut | None = None


class SearchRerankRequest(BaseModel):
    """Request body for POST /v1/search/rerank."""

    query: str = Field(..., description="Search query string")
    num_results: int = Field(10, ge=1, le=20, description="Number of results to return (1-20)")
    provider: str = Field("brave", description="Search provider name")


class SearchResultItem(BaseModel):
    """A single reranked search result."""

    title: str
    url: str
    snippet: str
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")


class SearchRerankResponse(BaseModel):
    """Response body for POST /v1/search/rerank."""

    query: str
    provider: str
    results: list[SearchResultItem]
    num_raw: int
    num_reranked: int


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer()


def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> str:
    """Validate the Bearer token against the BIND_TOOLS_API_KEY secret."""
    expected = os.environ.get("BIND_TOOLS_API_KEY", "")
    if not expected or credentials.credentials != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return credentials.credentials


# ---------------------------------------------------------------------------
# FastAPI app factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    """Build the FastAPI application with all routes."""

    api = FastAPI(
        title="bind-tools REST API",
        description="HTTP REST endpoints for Boltz structure prediction and GNINA molecular docking on Modal GPUs.",
        version="0.1.0",
    )

    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -- Health ---------------------------------------------------------------

    @api.get("/v1/health")
    async def health():
        return {"status": "ok"}

    # -- Boltz ----------------------------------------------------------------

    @api.post(
        "/v1/boltz/predict",
        response_model=BoltzPredictResponse,
        dependencies=[Depends(verify_bearer_token)],
    )
    async def boltz_predict(req: BoltzPredictRequest):
        from .boltz_remote import BoltzPredictor

        input_files = [f.to_bytes_dict() for f in req.input_files]

        raw: dict[str, Any] = BoltzPredictor().predict.remote(
            upstream_yaml=req.upstream_yaml,
            input_files=input_files,
            accelerator=req.accelerator,
            use_msa_server=req.use_msa_server,
            recycling_steps=req.recycling_steps,
            diffusion_samples=req.diffusion_samples,
            seed=req.seed,
        )

        # Encode output file bytes as base64
        output_files = [
            BoltzFileOut(
                name=f["name"],
                data=base64.b64encode(f["data"]).decode(),
            )
            for f in raw.get("output_files", [])
        ]

        return BoltzPredictResponse(
            returncode=raw["returncode"],
            stdout=raw.get("stdout", ""),
            stderr=raw.get("stderr", ""),
            output_files=output_files,
            confidence=raw.get("confidence"),
            affinity=raw.get("affinity"),
            primary_complex_path=raw.get("primary_complex_path"),
            structure_filenames=raw.get("structure_filenames", []),
        )

    # -- GNINA ----------------------------------------------------------------

    async def _gnina_handler(mode: str, req: GninaRequest) -> GninaResponse:
        from .gnina_remote import GninaRunner

        input_files = [f.to_bytes_dict() for f in req.input_files]

        raw: dict[str, Any] = GninaRunner().run.remote(
            mode=mode,
            gnina_args=req.gnina_args,
            input_files=input_files,
            output_filename=req.output_filename,
        )

        output_file = None
        if raw.get("output_file"):
            output_file = GninaFileOut(
                name=raw["output_file"]["name"],
                data=base64.b64encode(raw["output_file"]["data"]).decode(),
            )

        return GninaResponse(
            returncode=raw["returncode"],
            stdout=raw.get("stdout", ""),
            stderr=raw.get("stderr", ""),
            output_file=output_file,
        )

    @api.post(
        "/v1/gnina/dock",
        response_model=GninaResponse,
        dependencies=[Depends(verify_bearer_token)],
    )
    async def gnina_dock(req: GninaRequest):
        return await _gnina_handler("dock", req)

    @api.post(
        "/v1/gnina/score",
        response_model=GninaResponse,
        dependencies=[Depends(verify_bearer_token)],
    )
    async def gnina_score(req: GninaRequest):
        return await _gnina_handler("score", req)

    @api.post(
        "/v1/gnina/minimize",
        response_model=GninaResponse,
        dependencies=[Depends(verify_bearer_token)],
    )
    async def gnina_minimize(req: GninaRequest):
        return await _gnina_handler("minimize", req)

    # -- Search + Rerank ------------------------------------------------------

    @api.post(
        "/v1/search/rerank",
        response_model=SearchRerankResponse,
        dependencies=[Depends(verify_bearer_token)],
    )
    async def search_rerank(req: SearchRerankRequest):
        from .search_reranker import SearchReranker

        raw: dict = SearchReranker().search_and_rerank.remote(
            query=req.query,
            num_results=req.num_results,
            provider=req.provider,
        )
        return SearchRerankResponse(
            query=raw["query"],
            provider=raw["provider"],
            results=[SearchResultItem(**r) for r in raw["results"]],
            num_raw=raw["num_raw"],
            num_reranked=raw["num_reranked"],
        )

    return api


# ---------------------------------------------------------------------------
# Modal class — CPU-only web server
# ---------------------------------------------------------------------------


@app.cls(
    image=modal.Image.debian_slim(python_version="3.11").pip_install(
        "fastapi[standard]"
    ),
    secrets=[modal.Secret.from_name("bind-tools-api-key")],
    allow_concurrent_inputs=10,
    container_idle_timeout=600,
)
class WebAPI:
    """HTTP REST gateway that dispatches to GPU classes via .remote()."""

    @modal.asgi_app()
    def serve(self):
        return create_app()
