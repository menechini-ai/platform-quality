"""FastAPI application factory."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan: startup / shutdown."""
    logger.info("ObservAI starting up...")
    yield
    logger.info("ObservAI shutting down...")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    from app.health.router import router as health_router
    from app.incidents.router import router as incidents_router
    from app.rca.router import router as rca_router
    from app.self_healing.router import router as self_healing_router

    prefix = settings.API_V1_PREFIX
    app.include_router(incidents_router, prefix=prefix, tags=["incidents"])
    app.include_router(rca_router, prefix=prefix, tags=["rca"])
    app.include_router(health_router, prefix=prefix, tags=["health"])
    app.include_router(self_healing_router, prefix=prefix, tags=["self-healing"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
