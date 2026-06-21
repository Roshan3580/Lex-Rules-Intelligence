"""Demo reset — optional destructive for local demos (demo reset endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..middleware.rbac import require_role
from ..services import audit_service
from ..services.cache_service import invalidate_enforcement_caches

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset", response_model=schemas.DemoResetOut)
def demo_reset(
    request: Request,
    db: Session = Depends(get_db),
    _role: str = Depends(require_role("admin")),
):
    if not settings.demo_mode:
        raise HTTPException(
            status_code=403,
            detail="demo reset only enabled when DEMO_MODE=true",
        )
    n = db.query(models.OutcomeEvent).delete()
    db.commit()
    audit_service.log(
        db,
        action="demo_reset",
        resource_type="demo",
        resource_id="outcomes",
        actor=getattr(request.state, "user_id", None),
        detail={"deleted_outcomes": int(n or 0)},
    )
    invalidate_enforcement_caches()
    return schemas.DemoResetOut(deleted_outcomes=int(n or 0), status="ok")
