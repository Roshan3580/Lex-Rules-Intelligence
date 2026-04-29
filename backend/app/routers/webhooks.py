"""Webhook registration and delivery inspection."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/register", response_model=schemas.WebhookRegisterResponse)
def register_webhook(
    body: schemas.WebhookRegisterBody,
    db: Session = Depends(get_db),
):
    signing_secret = secrets.token_hex(32)
    wh = models.WebhookSubscription(
        tenant_id=body.tenant_id,
        url=body.url,
        events=body.events,
        secret_hint=signing_secret[:8],
        signing_secret=signing_secret,
        active=True,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return schemas.WebhookRegisterResponse(
        id=wh.id,
        url=wh.url,
        events=wh.events or [],
        active=bool(wh.active),
        secret_hint=wh.secret_hint,
        signing_secret=signing_secret,
    )


@router.get("/subscriptions", response_model=list[schemas.WebhookOut])
def list_subscriptions(
    db: Session = Depends(get_db),
    active_only: bool = True,
):
    q = db.query(models.WebhookSubscription).order_by(
        models.WebhookSubscription.created_at.desc()
    )
    if active_only:
        q = q.filter(models.WebhookSubscription.active.is_(True))
    rows = q.all()
    return [
        schemas.WebhookOut(
            id=r.id,
            url=r.url,
            events=r.events or [],
            active=bool(r.active),
            secret_hint=r.secret_hint,
        )
        for r in rows
    ]


@router.get("/deliveries", response_model=schemas.WebhookDeliveriesResponse)
def list_deliveries(
    db: Session = Depends(get_db),
    status: str | None = None,
    event_type: str | None = None,
    limit: int = Query(100, ge=1, le=500),
):
    q = db.query(models.WebhookDeliveryAttempt).order_by(
        models.WebhookDeliveryAttempt.created_at.desc()
    )
    if status:
        q = q.filter(models.WebhookDeliveryAttempt.status == status)
    if event_type:
        q = q.filter(models.WebhookDeliveryAttempt.event_type == event_type)
    rows = q.limit(limit).all()
    out = [
        schemas.WebhookDeliveryPublic(
            id=r.id,
            subscription_id=r.subscription_id,
            event_type=r.event_type,
            status=r.status,
            attempt_count=r.attempt_count,
            last_error=r.last_error,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return schemas.WebhookDeliveriesResponse(deliveries=out)
