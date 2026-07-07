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
    from app.datadog_routes.apm import router as apm_router
    from app.datadog_routes.error_tracking import router as error_tracking_router
    from app.datadog_routes.events import router as events_router
    from app.datadog_routes.logs import router as logs_router
    from app.datadog_routes.monitors import router as monitors_router
    from app.health.router import router as health_router
    from app.incidents.router import router as incidents_router
    from app.knowledge_base.router import router as kb_router
    from app.maturity.router import router as maturity_router
    from app.maturity.router_reports import router as reports_router
    from app.rca.router import router as rca_router
    from app.self_healing.router import router as self_healing_router

    prefix = settings.API_V1_PREFIX
    app.include_router(incidents_router, prefix=prefix, tags=["incidents"])
    app.include_router(rca_router, prefix=prefix, tags=["rca"])
    app.include_router(health_router, prefix=prefix, tags=["health"])
    app.include_router(self_healing_router, prefix=prefix, tags=["self-healing"])
    app.include_router(maturity_router, prefix=prefix, tags=["maturity"])
    app.include_router(reports_router, prefix=prefix, tags=["reports"])
    app.include_router(monitors_router, prefix=prefix, tags=["datadog-monitors"])
    app.include_router(events_router, prefix=prefix, tags=["datadog-events"])
    app.include_router(error_tracking_router, prefix=prefix, tags=["datadog-errors"])
    app.include_router(logs_router, prefix=prefix, tags=["datadog-logs"])
    app.include_router(apm_router, prefix=prefix, tags=["datadog-apm"])
    app.include_router(kb_router, prefix=prefix, tags=["knowledge-base"])

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    return app


app = create_app()
