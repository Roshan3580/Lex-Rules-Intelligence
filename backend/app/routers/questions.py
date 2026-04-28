"""Q&A endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
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
        top_k=payload.top_k,
    )
