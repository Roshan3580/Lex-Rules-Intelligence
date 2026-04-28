"""FastAPI application entrypoint.

This is a modular monolith: ingestion, extraction, retrieval, answering,
and review all live in the same process but behind clean service
boundaries (see app/services/). Routers are thin and only validate +
delegate to services.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import SessionLocal, init_db
from .routers import questions, review, rules, sources
from .schemas import HealthOut
from .seed import seed_if_empty

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(
        title="State Tax Rules Intelligence Platform",
        version="0.1.0",
        description=(
            "Turn fragmented state tax law sources into structured, "
            "searchable, source-backed workflow intelligence."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin, "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(sources.router)
    app.include_router(rules.router)
    app.include_router(questions.router)
    app.include_router(review.router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        with SessionLocal() as db:
            inserted = seed_if_empty(db)
            if inserted:
                logger.info("Seeded %d demo rules across CA, TX, NY", inserted)
        logger.info(
            "Backend ready (LLM enabled: %s, model: %s)",
            settings.llm_enabled,
            settings.llm_model if settings.llm_enabled else "fallback",
        )

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(
            status="ok",
            llm_enabled=settings.llm_enabled,
            database=settings.database_url.split("://", 1)[0],
        )

    return app


app = create_app()
