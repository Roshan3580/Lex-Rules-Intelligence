"""Demo reset — optional destructive for local demos (Brief §10)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db

router = APIRouter(prefix="/api/demo", tags=["demo"])


@router.post("/reset", response_model=schemas.DemoResetOut)
def demo_reset(db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(
            status_code=403,
            detail="demo reset only enabled when DEMO_MODE=true",
        )
    n = db.query(models.OutcomeEvent).delete()
    db.commit()
    return schemas.DemoResetOut(deleted_outcomes=int(n or 0), status="ok")
