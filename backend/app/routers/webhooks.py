"""Webhook registration and delivery inspection."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..middleware.rbac import require_role
from ..services.webhook_delivery_service import resend_delivery_attempt

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/register", response_model=schemas.WebhookRegisterResponse)
def register_webhook(
    body: schemas.WebhookRegisterBody,
    request: Request,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
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
    from ..services import audit_service

    audit_service.log(
        db,
        action="webhook_registered",
        resource_type="webhook_subscription",
        resource_id=wh.id,
        actor=getattr(request.state, "user_id", None),
        detail={
            "url": wh.url,
            "events": list(wh.events or []),
            "tenant_id": body.tenant_id,
        },
    )
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
            response_status_code=getattr(r, "response_status_code", None),
            response_body_preview=getattr(r, "response_body_preview", None),
            duration_ms=getattr(r, "duration_ms", None),
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]
    return schemas.WebhookDeliveriesResponse(deliveries=out)


@router.post(
    "/deliveries/{delivery_id}/resend",
    response_model=schemas.WebhookDeliveryPublic,
)
def resend_delivery(
    delivery_id: str,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    try:
        attempt = resend_delivery_attempt(db, delivery_id=delivery_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="Delivery not found")
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "invalid_delivery", "message": str(exc)},
        )
    return schemas.WebhookDeliveryPublic(
        id=attempt.id,
        subscription_id=attempt.subscription_id,
        event_type=attempt.event_type,
        status=attempt.status,
        attempt_count=attempt.attempt_count,
        last_error=attempt.last_error,
        response_status_code=attempt.response_status_code,
        response_body_preview=attempt.response_body_preview,
        duration_ms=attempt.duration_ms,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
    )


@router.get("/health", response_model=schemas.WebhookHealthOut)
def webhook_health(
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("reviewer")),
):
    now = datetime.utcnow()
    since = now - timedelta(hours=24)
    total_subs = int(db.query(func.count(models.WebhookSubscription.id)).scalar() or 0)
    active_subs = int(
        db.query(func.count(models.WebhookSubscription.id))
        .filter(models.WebhookSubscription.active.is_(True))
        .scalar()
        or 0
    )
    deliveries_last_24h = int(
        db.query(func.count(models.WebhookDeliveryAttempt.id))
        .filter(models.WebhookDeliveryAttempt.created_at >= since)
        .scalar()
        or 0
    )
    success_last_24h = int(
        db.query(func.count(models.WebhookDeliveryAttempt.id))
        .filter(models.WebhookDeliveryAttempt.created_at >= since)
        .filter(models.WebhookDeliveryAttempt.status == "success")
        .scalar()
        or 0
    )
    failed_last_24h = int(
        db.query(func.count(models.WebhookDeliveryAttempt.id))
        .filter(models.WebhookDeliveryAttempt.created_at >= since)
        .filter(models.WebhookDeliveryAttempt.status == "failed")
        .scalar()
        or 0
    )
    success_rate = (
        float(success_last_24h) / float(deliveries_last_24h)
        if deliveries_last_24h > 0
        else 1.0
    )

    recent = (
        db.query(models.WebhookDeliveryAttempt, models.WebhookSubscription)
        .join(
            models.WebhookSubscription,
            models.WebhookSubscription.id == models.WebhookDeliveryAttempt.subscription_id,
        )
        .filter(models.WebhookDeliveryAttempt.created_at >= since)
        .filter(models.WebhookDeliveryAttempt.status == "failed")
        .order_by(models.WebhookDeliveryAttempt.created_at.desc())
        .limit(10)
        .all()
    )
    failures = [
        schemas.WebhookFailurePublic(
            id=a.id,
            url=s.url,
            event_type=a.event_type,
            last_error=a.last_error,
            created_at=a.created_at,
        )
        for a, s in recent
    ]

    return schemas.WebhookHealthOut(
        total_subscriptions=total_subs,
        active_subscriptions=active_subs,
        deliveries_last_24h=deliveries_last_24h,
        success_last_24h=success_last_24h,
        failed_last_24h=failed_last_24h,
        success_rate_last_24h=success_rate,
        recent_failures=failures,
    )
