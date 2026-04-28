"""Lightweight metadata endpoints: /health, /api/states."""

from __future__ import annotations

from fastapi import APIRouter

from .. import schemas
from ..config import settings

router = APIRouter(tags=["meta"])


# Canonical 50-state list with USPS abbreviations.
_US_STATES: list[tuple[str, str]] = [
    ("Alabama", "AL"), ("Alaska", "AK"), ("Arizona", "AZ"), ("Arkansas", "AR"),
    ("California", "CA"), ("Colorado", "CO"), ("Connecticut", "CT"),
    ("Delaware", "DE"), ("Florida", "FL"), ("Georgia", "GA"), ("Hawaii", "HI"),
    ("Idaho", "ID"), ("Illinois", "IL"), ("Indiana", "IN"), ("Iowa", "IA"),
    ("Kansas", "KS"), ("Kentucky", "KY"), ("Louisiana", "LA"), ("Maine", "ME"),
    ("Maryland", "MD"), ("Massachusetts", "MA"), ("Michigan", "MI"),
    ("Minnesota", "MN"), ("Mississippi", "MS"), ("Missouri", "MO"),
    ("Montana", "MT"), ("Nebraska", "NE"), ("Nevada", "NV"),
    ("New Hampshire", "NH"), ("New Jersey", "NJ"), ("New Mexico", "NM"),
    ("New York", "NY"), ("North Carolina", "NC"), ("North Dakota", "ND"),
    ("Ohio", "OH"), ("Oklahoma", "OK"), ("Oregon", "OR"),
    ("Pennsylvania", "PA"), ("Rhode Island", "RI"), ("South Carolina", "SC"),
    ("South Dakota", "SD"), ("Tennessee", "TN"), ("Texas", "TX"),
    ("Utah", "UT"), ("Vermont", "VT"), ("Virginia", "VA"),
    ("Washington", "WA"), ("West Virginia", "WV"), ("Wisconsin", "WI"),
    ("Wyoming", "WY"),
]


@router.get("/health", response_model=schemas.HealthOut)
def health() -> schemas.HealthOut:
    """Top-level health probe (also exposed at /api/health)."""
    return schemas.HealthOut(
        status="ok",
        llm_enabled=settings.llm_enabled,
        database=settings.database_url.split("://", 1)[0],
    )


@router.get("/api/states", response_model=list[schemas.StateOut])
def list_states() -> list[schemas.StateOut]:
    return [schemas.StateOut(name=n, abbreviation=a) for n, a in _US_STATES]
