"""Lightweight periodic jobs — APScheduler optional."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
_scheduler = None


def configure_scheduler(session_factory: type[Session]) -> None:
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.info("APScheduler not installed — scheduled ingestion disabled.")
        return
    if _scheduler is not None:
        return

    def tick() -> None:
        logger.debug("scheduled tick — wire monitor_run here if desired.")

    sch = BackgroundScheduler()
    sch.add_job(tick, "interval", minutes=360, id="noop_maintenance_tick")
    sch.start()
    _scheduler = sch
    logger.info("Background scheduler started (interval jobs are no-op stubs).")


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
