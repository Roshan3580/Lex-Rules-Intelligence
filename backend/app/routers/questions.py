"""Q&A endpoints (/api/ask and /api/query)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import answer_service

router = APIRouter(prefix="/api", tags=["questions"])


@router.post("/ask", response_model=schemas.AnswerOut)
def ask(payload: schemas.AskRequest, db: Session = Depends(get_db)):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")
    return answer_service.answer_question(
        db,
        question=payload.question,
        state=payload.state,
        tax_category=payload.tax_category,
        workflow_stage=payload.workflow_stage,
        operating_scenario=payload.operating_scenario,
        statuses=payload.statuses,
        top_k=payload.top_k,
    )


@router.post("/query", response_model=schemas.QueryResponse)
def query(payload: schemas.QueryRequest, db: Session = Depends(get_db)):
    """Spec-shaped Q&A endpoint.

    Same retrieval + grounding logic as /api/ask, but emits the response
    shape the brief / frontend expects: { answer, state, tax_type,
    sources[], confidence, ... }.
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Empty question")

    answer = answer_service.answer_question(
        db,
        question=payload.question,
        state=payload.state,
        tax_category=payload.tax_type,
        workflow_stage=payload.workflow_stage,
        operating_scenario=payload.operating_scenario,
        statuses=payload.statuses,
        top_k=payload.top_k,
    )

    sources: list[schemas.QuerySource] = []
    for c in answer.citations:
        document_type = "rule" if c.rule_id else _document_type_for_source(
            db, c.source_id
        )
        last_checked = _last_checked_for_source(db, c.source_id)
        title = c.source_name or (c.rule_id and "Extracted rule") or "Source"
        sources.append(
            schemas.QuerySource(
                title=title,
                url=c.source_url,
                snippet=c.snippet,
                document_type=document_type,
                last_checked=last_checked,
                state=c.state,
                tax_type=c.tax_category,
                relevance=c.relevance,
            )
        )

    return schemas.QueryResponse(
        answer=answer.answer,
        state=answer.state,
        tax_type=answer.tax_category,
        sources=sources,
        confidence=answer.confidence_score,
        method=answer.method,
        retrieval_mode=answer.retrieval_mode,
        rules_used=answer.rules_used,
        question_id=answer.question_id,
        answered_at=answer.created_at,
    )


def _document_type_for_source(db: Session, source_id: str | None) -> str:
    if not source_id:
        return "snippet"
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not src:
        return "snippet"
    return {
        "url": "webpage",
        "pdf": "pdf",
        "text": "manual",
        "manual": "manual",
        "upload": "upload",
    }.get(src.source_type, src.source_type)


def _last_checked_for_source(db: Session, source_id: str | None):
    if not source_id:
        return None
    src = db.query(models.Source).filter(models.Source.id == source_id).first()
    if not src:
        return None
    return src.last_checked or src.updated_at
