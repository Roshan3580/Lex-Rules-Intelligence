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
from .routers import (
    admin,
    analytics,
    dashboard,
    demo,
    ingest,
    meta,
    monitor,
    platform,
    questions,
    review,
    rules,
    sources,
    submission_intel,
    validation,
    webhooks,
    workflows,
)
from .schemas import HealthOut
from .seed import ensure_demo_enforcement_rules, seed_if_empty

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
        allow_origins=[
            settings.frontend_origin,
            "http://localhost:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(meta.router)
    app.include_router(sources.router)
    app.include_router(rules.router)
    app.include_router(questions.router)
    app.include_router(review.router)
    app.include_router(validation.router)
    app.include_router(ingest.router)
    app.include_router(workflows.router)
    app.include_router(submission_intel.router)
    app.include_router(webhooks.router)
    app.include_router(platform.router)
    app.include_router(demo.router)
    app.include_router(admin.router)
    app.include_router(dashboard.router)
    app.include_router(analytics.router)
    app.include_router(monitor.router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        with SessionLocal() as db:
            from .services import governance_service, workflows_service

            workflows_service.ensure_default_templates(db)
            governance_service.ensure_jurisdiction_seed(db)
            governance_service.ensure_rejection_reason_seed(db)
        if settings.demo_mode:
            with SessionLocal() as db:
                inserted = seed_if_empty(db)
                if inserted:
                    logger.info(
                        "DEMO_MODE: seeded %d illustrative rules across CA, TX, NY",
                        inserted,
                    )
                else:
                    logger.info(
                        "DEMO_MODE: rules table already populated, skipping full seed"
                    )
                ensured = ensure_demo_enforcement_rules(db)
                if ensured:
                    logger.info(
                        "DEMO_MODE: ensured %d Submission Validator enforcement demo rule(s)",
                        ensured,
                    )
        else:
            logger.info(
                "DEMO_MODE off: skipping illustrative seed. "
                "Use POST /api/ingest/run or upload sources to populate."
            )
        logger.info(
            "Backend ready (LLM enabled: %s, model: %s, demo_mode: %s)",
            settings.llm_enabled,
            settings.llm_model if settings.llm_enabled else "fallback",
            settings.demo_mode,
        )
        from .services import scheduler_service

        scheduler_service.configure_scheduler()


    @app.on_event("shutdown")
    def _shutdown() -> None:
        from .services import scheduler_service

        scheduler_service.shutdown_scheduler()

    @app.get("/api/health", response_model=HealthOut)
    def health() -> HealthOut:
        return HealthOut(
            status="ok",
            llm_enabled=settings.llm_enabled,
            database=settings.database_url.split("://", 1)[0],
            demo_mode=settings.demo_mode,
        )

    return app


app = create_app()
