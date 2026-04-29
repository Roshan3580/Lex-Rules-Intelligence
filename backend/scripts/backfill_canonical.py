#!/usr/bin/env python3
"""CLI for canonical FK backfill (jurisdiction, program variant, rejection links)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db  # noqa: E402
from app.services.backfill_service import Target, run_backfill  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill normalized rule FK fields.")
    p.add_argument(
        "--target",
        default="all",
        choices=["all", "jurisdictions", "program_variants", "rejection_links"],
        help="Which backfill to run",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes (omit for dry-run plan only)",
    )
    args = p.parse_args()
    dry_run = not args.apply

    init_db()
    db = SessionLocal()
    try:
        target: Target = args.target  # type: ignore[assignment]
        changes, summary = run_backfill(db, target=target, dry_run=dry_run)
        if not dry_run:
            db.commit()
        print("summary:", summary)
        print("change_records:", len(changes))
        return 0
    except Exception as exc:  # pragma: no cover
        db.rollback()
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
