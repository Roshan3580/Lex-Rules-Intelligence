"""Outbound webhook HTTP delivery with retries and HMAC (non-blocking enqueue)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from .. import models
from ..database import SessionLocal

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 30.0
MAX_ATTEMPTS = 3
# After attempt 1 and 2 fail, wait before attempt 2 and 3 (3 attempts total).
BACKOFF_SECS = (1.0, 5.0)


def subscription_wants_event(sub: models.WebhookSubscription, event_type: str) -> bool:
    evs = sub.events or []
    if not evs:
        return True
    if "*" in evs:
        return True
    return event_type in evs


def schedule_send_event(
    background_tasks: BackgroundTasks,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Queue delivery in FastAPI's background task runner (does not block the response)."""

    def _job() -> None:
        try:
            with SessionLocal() as db:
                send_event_sync(db, event_type, payload)
        except Exception:
            logger.exception(
                "webhook background job failed event_type=%s", event_type
            )

    background_tasks.add_task(_job)


def send_event_sync(db: Session, event_type: str, payload: dict[str, Any]) -> None:
    """Process all active subscriptions for this event (sync; used from background job)."""
    subs = (
        db.query(models.WebhookSubscription)
        .filter(models.WebhookSubscription.active.is_(True))
        .all()
    )
    for sub in subs:
        if not subscription_wants_event(sub, event_type):
            continue
        envelope: dict[str, Any] = {"event": event_type, "data": payload}
        attempt = models.WebhookDeliveryAttempt(
            subscription_id=sub.id,
            event_type=event_type,
            payload=envelope,
            status="pending",
            attempt_count=0,
            last_error=None,
        )
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        try:
            dispatch_to_subscriber(db, attempt, sub)
        except Exception:
            logger.exception(
                "dispatch_to_subscriber crashed subscription_id=%s attempt_id=%s",
                sub.id,
                attempt.id,
            )


def dispatch_to_subscriber(
    db: Session,
    attempt: models.WebhookDeliveryAttempt,
    sub: models.WebhookSubscription,
) -> None:
    """POST with up to ``MAX_ATTEMPTS`` tries and exponential-style backoff on failure."""
    body_dict = attempt.payload
    body_str = json.dumps(body_dict, separators=(",", ":"), sort_keys=True)
    body_bytes = body_str.encode("utf-8")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    secret = (sub.signing_secret or "").strip() or None

    for i in range(MAX_ATTEMPTS):
        attempt.attempt_count = i + 1
        attempt.updated_at = datetime.utcnow()
        db.commit()

        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Event-Type": attempt.event_type,
            "X-Timestamp": ts,
        }
        if secret:
            sig = hmac.new(
                secret.encode("utf-8"), body_bytes, hashlib.sha256
            ).hexdigest()
            headers["X-Signature"] = f"sha256={sig}"

        try:
            with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
                r = client.post(sub.url, content=body_bytes, headers=headers)
            if 200 <= r.status_code < 300:
                attempt.status = "success"
                attempt.last_error = None
                attempt.updated_at = datetime.utcnow()
                db.commit()
                logger.info(
                    "webhook ok event=%s subscription=%s attempt=%s http=%s",
                    attempt.event_type,
                    sub.id,
                    attempt.attempt_count,
                    r.status_code,
                )
                return
            err_msg = f"HTTP {r.status_code}: {r.text[:500]}"
        except Exception as exc:
            err_msg = f"{type(exc).__name__}: {exc}"[:2000]

        attempt.last_error = err_msg
        attempt.status = "pending"
        attempt.updated_at = datetime.utcnow()
        db.commit()
        logger.warning(
            "webhook attempt failed event=%s subscription=%s try=%s error=%s",
            attempt.event_type,
            sub.id,
            i + 1,
            err_msg[:200],
        )

        if i < MAX_ATTEMPTS - 1:
            delay = BACKOFF_SECS[i] if i < len(BACKOFF_SECS) else 15.0
            time.sleep(delay)

    attempt.status = "failed"
    attempt.updated_at = datetime.utcnow()
    db.commit()
    logger.error(
        "webhook exhausted retries event=%s subscription=%s last_error=%s",
        attempt.event_type,
        sub.id,
        (attempt.last_error or "")[:300],
    )
