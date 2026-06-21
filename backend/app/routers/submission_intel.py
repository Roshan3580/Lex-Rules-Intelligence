"""Submission intelligence — filing paths and portal metadata."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import submission_service

router = APIRouter(prefix="/api", tags=["submission intelligence"])


@router.get("/submission-path", response_model=schemas.SubmissionPathOut)
def submission_path(
    state: str = Query(...),
    tax_category: str = Query(...),
    workflow_stage: str | None = None,
    transaction_type: str | None = None,
    db: Session = Depends(get_db),
):
    data = submission_service.build_submission_path(
        db,
        state=state,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        transaction_type=transaction_type,
    )
    return schemas.SubmissionPathOut(**data)
