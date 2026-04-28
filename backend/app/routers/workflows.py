"""Workflow guidance endpoints (Phase 7).

Surfaces the four routes called out in the upgrade plan:

    GET   /api/workflows/templates
    POST  /api/workflows/cases
    GET   /api/workflows/cases/{id}
    PATCH /api/workflows/cases/{id}/steps

Plus a few read-side helpers (`GET /api/workflows/templates/{id}`,
`GET /api/workflows/cases`) that the frontend Workflows page needs to
list/select existing cases.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..database import get_db
from ..services import workflows_service

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("/templates", response_model=list[schemas.WorkflowTemplateOut])
def list_templates(
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return workflows_service.list_templates(
        db, state=state, tax_category=tax_category, attach_rules=True
    )


@router.get("/templates/{template_id}", response_model=schemas.WorkflowTemplateOut)
def get_template(
    template_id: str,
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    db: Session = Depends(get_db),
):
    tpl = workflows_service.get_template(
        db, template_id, state=state, tax_category=tax_category
    )
    if tpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.post("/cases", response_model=schemas.CaseWorkflowOut)
def create_case(
    payload: schemas.CreateCaseRequest,
    db: Session = Depends(get_db),
):
    try:
        return workflows_service.create_case(
            db,
            state=payload.state,
            tax_category=payload.tax_category,
            title=payload.title,
            org=payload.org,
            template_id=payload.template_id,
            case_id=payload.case_id,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/cases", response_model=list[schemas.CaseWorkflowOut])
def list_cases(
    state: Optional[str] = None,
    tax_category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    return workflows_service.list_cases(
        db, state=state, tax_category=tax_category, status=status, limit=limit
    )


@router.get("/cases/{case_id}", response_model=schemas.CaseWorkflowOut)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = workflows_service.get_case(db, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


@router.patch("/cases/{case_id}/steps", response_model=schemas.CaseWorkflowOut)
def update_step(
    case_id: str,
    payload: schemas.UpdateStepRequest,
    db: Session = Depends(get_db),
):
    try:
        case = workflows_service.update_step(
            db,
            case_id,
            payload.step_key,
            completed=payload.completed,
            notes=payload.notes,
            actor=payload.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return case
