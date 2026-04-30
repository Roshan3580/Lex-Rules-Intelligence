"""SQLAlchemy engine + session setup.

We use a synchronous engine for prototype simplicity. SQLite is the default
(zero-setup), but the same code path works against PostgreSQL by setting
DATABASE_URL.
"""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        # check_same_thread=False is required because FastAPI may serve
        # requests from different threads against the same connection.
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables. Called once on startup."""
    # Import models so they register with Base.metadata before create_all.
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_rules_phase2_columns()
    _ensure_governance_v1_columns()
    _ensure_webhook_signing_secret_column()
    _ensure_webhook_attempt_telemetry_columns()


def _ensure_governance_v1_columns() -> None:
    """Add Engineer Brief v1 governance columns and tenant ids (SQLite + PG)."""
    from sqlalchemy import inspect, text

    dialect = engine.dialect.name

    def add_cols(table: str, columns: list[tuple[str, str]]) -> None:
        try:
            insp = inspect(engine)
            if table not in insp.get_table_names():
                return
            have = {c["name"] for c in insp.get_columns(table)}
        except Exception:  # pragma: no cover
            return
        ddl: list[str] = []
        for name, sqltype in columns:
            if name in have:
                continue
            if dialect == "postgresql":
                ddl.append(f'ALTER TABLE "{table}" ADD COLUMN IF NOT EXISTS {name} {sqltype}')
            else:
                ddl.append(f"ALTER TABLE {table} ADD COLUMN {name} {sqltype}")
        if not ddl:
            return
        try:
            with engine.begin() as conn:
                for stmt in ddl:
                    conn.execute(text(stmt))
        except Exception:  # pragma: no cover
            pass

    rule_cols = [
        ("program_variant_ref_id", "VARCHAR(64)"),
        ("jurisdiction_id", "VARCHAR(64)"),
        ("tenant_id", "VARCHAR(64) DEFAULT 'default'"),
        ("operating_scenario_json", "TEXT"),
        ("filing_timing", "TEXT"),
        ("required_actions_structured", "TEXT"),
        ("submission_portal_url", "VARCHAR(1024)"),
        ("submission_endpoint_urls", "TEXT"),
        ("portal_instructions", "TEXT"),
        ("superseded_by_rule_id", "VARCHAR(64)"),
        ("superseded_at", "DATETIME"),
        ("extraction_run_id", "VARCHAR(64)"),
        ("extractor_model_version", "VARCHAR(128)"),
        ("extractor_prompt_version", "VARCHAR(64)"),
        ("reviewer_user_id", "VARCHAR(128)"),
    ]
    if dialect == "postgresql":
        rule_cols = [
            ("program_variant_ref_id", "VARCHAR(64)"),
            ("jurisdiction_id", "VARCHAR(64)"),
            ("tenant_id", "VARCHAR(64) DEFAULT 'default'"),
            ("operating_scenario_json", "JSONB"),
            ("filing_timing", "JSONB"),
            ("required_actions_structured", "JSONB"),
            ("submission_portal_url", "VARCHAR(1024)"),
            ("submission_endpoint_urls", "JSONB"),
            ("portal_instructions", "TEXT"),
            ("superseded_by_rule_id", "VARCHAR(64)"),
            ("superseded_at", "TIMESTAMP"),
            ("extraction_run_id", "VARCHAR(64)"),
            ("extractor_model_version", "VARCHAR(128)"),
            ("extractor_prompt_version", "VARCHAR(64)"),
            ("reviewer_user_id", "VARCHAR(128)"),
        ]

    add_cols("rules", rule_cols)

    src_cols = [("tenant_id", "VARCHAR(64) DEFAULT 'default'")]
    add_cols("sources", src_cols)

    add_cols(
        "outcome_events",
        [("tenant_id", "VARCHAR(64) DEFAULT 'default'")],
    )

    wt_cols = [("tenant_id", "VARCHAR(64) DEFAULT 'default'")]
    add_cols("workflow_templates", wt_cols)

    cw_cols = [
        ("tenant_id", "VARCHAR(64) DEFAULT 'default'"),
        ("validation_payload", "TEXT"),
    ]
    if dialect == "postgresql":
        cw_cols = [("tenant_id", "VARCHAR(64) DEFAULT 'default'"), ("validation_payload", "JSONB")]
    add_cols("case_workflows", cw_cols)


def _ensure_webhook_signing_secret_column() -> None:
    """Add HMAC signing column for existing ``webhook_subscriptions`` rows."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "webhook_subscriptions" not in insp.get_table_names():
            return
        have = {c["name"] for c in insp.get_columns("webhook_subscriptions")}
    except Exception:  # pragma: no cover
        return
    if "signing_secret" in have:
        return
    dialect = engine.dialect.name
    stmt = (
        "ALTER TABLE webhook_subscriptions ADD COLUMN IF NOT EXISTS signing_secret VARCHAR(256)"
        if dialect == "postgresql"
        else "ALTER TABLE webhook_subscriptions ADD COLUMN signing_secret VARCHAR(256)"
    )
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
    except Exception:  # pragma: no cover
        pass


def _ensure_webhook_attempt_telemetry_columns() -> None:
    """Add response telemetry columns on existing delivery attempts."""
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "webhook_delivery_attempts" not in insp.get_table_names():
            return
        have = {c["name"] for c in insp.get_columns("webhook_delivery_attempts")}
    except Exception:  # pragma: no cover
        return

    cols: list[tuple[str, str]] = [
        ("response_status_code", "INTEGER"),
        ("response_body_preview", "TEXT"),
        ("duration_ms", "INTEGER"),
    ]
    dialect = engine.dialect.name
    ddl: list[str] = []
    for name, sqltype in cols:
        if name in have:
            continue
        if dialect == "postgresql":
            ddl.append(
                f'ALTER TABLE "webhook_delivery_attempts" ADD COLUMN IF NOT EXISTS {name} {sqltype}'
            )
        else:
            ddl.append(
                f"ALTER TABLE webhook_delivery_attempts ADD COLUMN {name} {sqltype}"
            )
    if not ddl:
        return
    try:
        with engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))
    except Exception:  # pragma: no cover
        pass


def _ensure_rules_phase2_columns() -> None:
    """Add Phase 2 governance columns on existing DBs (SQLite + Postgres).

    SQLAlchemy ``create_all`` does not ALTER existing tables; lightweight
    migrations keep Engineer Brief fields (§6 program_variant, effective
    range) available without wiping ``rules.db``.
    """
    from sqlalchemy import inspect, text

    try:
        insp = inspect(engine)
        if "rules" not in insp.get_table_names():
            return
        have = {c["name"] for c in insp.get_columns("rules")}
    except Exception:  # pragma: no cover
        return

    ddl: list[str] = []
    dialect = engine.dialect.name
    if "program_variant" not in have:
        if dialect == "postgresql":
            ddl.append("ALTER TABLE rules ADD COLUMN IF NOT EXISTS program_variant JSONB")
        else:
            ddl.append("ALTER TABLE rules ADD COLUMN program_variant TEXT")
    if "effective_date_end" not in have:
        if dialect == "postgresql":
            ddl.append(
                "ALTER TABLE rules ADD COLUMN IF NOT EXISTS effective_date_end VARCHAR(64)"
            )
        else:
            ddl.append("ALTER TABLE rules ADD COLUMN effective_date_end VARCHAR(64)")

    if not ddl:
        return
    try:
        with engine.begin() as conn:
            for stmt in ddl:
                conn.execute(text(stmt))
    except Exception:  # pragma: no cover - idempotent retries
        pass
