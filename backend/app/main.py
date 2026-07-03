"""AEGIS — Autonomous Engagement & Generative Intelligence System.

FastAPI entry point: logging → database init → CORS → routes.
Run locally:  uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router as api_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.engine import dispose_engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    log = structlog.get_logger()

    if not settings.anthropic_api_key:
        log.warning("anthropic_api_key_missing — set ANTHROPIC_API_KEY in .env")

    await init_db()
    log.info("aegis_started", version="2.0.0", db=settings.database_url.split("@")[-1])
    yield
    await dispose_engine()
    log.info("aegis_shutting_down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AEGIS",
        description="Autonomous Engagement & Generative Intelligence System",
        version="2.0.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")

    @app.get("/")
    async def root():
        return {
            "name": "AEGIS",
            "tagline": "Autonomous Engagement & Generative Intelligence System",
            "docs": "/docs",
            "health": "/api/health",
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
