"""FastAPI application factory."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title="BindingOps API",
        version="0.1.0",
        description="API for protein-ligand binding analysis platform",
    )

    # CORS
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in origins.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Ensure DB schema on startup
    @app.on_event("startup")
    def _ensure_schema() -> None:
        try:
            from bind_tools.db import DbRecorder

            DbRecorder.ensure_schema()
            logger.info("Database schema ensured")
        except Exception:
            logger.warning("Could not ensure DB schema (DB may not be configured)")

    # Mount routers
    from bind_tools.api.routes.agents import router as agents_router
    from bind_tools.api.routes.artifacts import router as artifacts_router
    from bind_tools.api.routes.runs import router as runs_router
    from bind_tools.api.routes.ws import router as ws_router

    app.include_router(agents_router)
    app.include_router(runs_router)
    app.include_router(artifacts_router)
    app.include_router(ws_router)

    return app
