"""Idempotent backfill for normalized Rule FKs (jurisdiction, program variant, rejection links)."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from typing import Any, Literal, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models
from .rule_engine import _STATE_ABBR, normalize_state

Target = Literal["all", "jurisdictions", "program_variants", "rejection_links"]


def _slug(s: str, max_len: int = 120) -> str:
    t = re.sub(r"[^a-z0-9_]+", "_", (s or "").lower()).strip("_")
    return (t[:max_len] if t else "variant")[:max_len]


def state_to_us_code(state: Optional[str]) -> Optional[str]:
    """Map ``Rule.state`` to a ``US-XX`` jurisdiction code, or None."""
    if not state or not str(state).strip():
        return None
    raw = str(state).strip()
    low = raw.lower()
    if low in ("unknown", "n/a", "—", "-"):
        return None
    n = normalize_state(raw)
    if not n:
        return None
    if len(raw) == 2 and len(n) > 2:
        abbr = raw.upper()
        if abbr in _STATE_ABBR:
            return f"US-{abbr}"
    for abbr, full in _STATE_ABBR.items():
        if full == n:
            return f"US-{abbr}"
    return None


def _display_name_for_us_code(code: str) -> str:
    if code.startswith("US-") and len(code) == 5:
        abbr = code[3:5]
        return _STATE_ABBR.get(abbr, code)
    return code


def find_jurisdiction_id_by_code(db: Session, code: str) -> Optional[str]:
    row = (
        db.query(models.Jurisdiction)
        .filter(models.Jurisdiction.code == code)
        .first()
    )
    return row.id if row else None


def ensure_jurisdiction_row(
    db: Session,
    state: str,
    *,
    apply: bool,
    scratch: Optional[dict[str, str]] = None,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    """Return jurisdiction id (real or dry-run placeholder). ``scratch`` dedupes dry-run peers."""
    code = state_to_us_code(state)
    if not code:
        return None, None
    jid = find_jurisdiction_id_by_code(db, code)
    if jid:
        return jid, None

    dn = _display_name_for_us_code(code)
    if apply:
        j = models.Jurisdiction(code=code, display_name=dn)
        db.add(j)
        db.flush()
        return j.id, None

    assert scratch is not None
    if code in scratch:
        return scratch[code], None
    plan = {"kind": "create_jurisdiction", "code": code, "display_name": dn}
    pending = f"__pending_jurisdiction__:{code}"
    scratch[code] = pending
    return pending, plan


def derive_program_variant_def(
    program_variant: dict[str, Any],
    *,
    jurisdiction_id: Optional[str],
) -> tuple[str, str, dict[str, Any]]:
    """Build key_slug, label, meta for ProgramVariantDef."""
    pk = program_variant.get("program_key")
    pname = program_variant.get("program_name") or program_variant.get("tax_program")
    vtype = program_variant.get("variant_type") or program_variant.get("cadence")
    parts = [x for x in (pk, pname, vtype) if x]
    label = " · ".join(str(p) for p in parts) if parts else "Default program variant"
    if pk:
        key_base = _slug(str(pk))
    else:
        raw = f"{pname or 'tp'}|{vtype or 'base'}"
        key_base = _slug(raw)
    if not key_base:
        raw_bytes = stable_json_bytes(program_variant)
        key_base = "pv_" + hashlib.sha256(raw_bytes).hexdigest()[:16]
    meta: dict[str, Any] = {"source": "backfill"}
    if jurisdiction_id:
        meta["jurisdiction_id"] = jurisdiction_id
    if vtype:
        meta["variant_type"] = vtype
    return key_base, label[:255], meta


def stable_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode(
        "utf-8"
    )


def find_program_variant_def_by_slug(
    db: Session, key_slug: str
) -> Optional[models.ProgramVariantDef]:
    return (
        db.query(models.ProgramVariantDef)
        .filter(models.ProgramVariantDef.key_slug == key_slug)
        .first()
    )


def ensure_program_variant_def_id(
    db: Session,
    program_variant: dict[str, Any],
    *,
    jurisdiction_id: Optional[str],
    apply: bool,
    scratch: Optional[dict[str, str]] = None,
) -> tuple[Optional[str], list[dict[str, Any]]]:
    """Find or create ProgramVariantDef; return id and create plans (no duplicate slugs)."""
    key_slug, label, meta = derive_program_variant_def(
        program_variant, jurisdiction_id=jurisdiction_id
    )
    existing = find_program_variant_def_by_slug(db, key_slug)
    if existing:
        return existing.id, []

    plan = {
        "kind": "create_program_variant_def",
        "key_slug": key_slug,
        "label": label,
    }
    if not apply:
        assert scratch is not None
        if key_slug in scratch:
            return scratch[key_slug], []
        pending = f"__pending_program_variant__:{key_slug}"
        scratch[key_slug] = pending
        return pending, [plan]

    pv = models.ProgramVariantDef(key_slug=key_slug, label=label, meta=meta)
    db.add(pv)
    db.flush()
    return pv.id, []


def _rejection_pairs_from_rule(rule: models.Rule) -> list[tuple[str, str]]:
    """Return (code, label) pairs from lineage / program_variant JSON."""
    out: list[tuple[str, str]] = []
    pv = rule.program_variant if isinstance(rule.program_variant, dict) else {}
    lin = rule.lineage if isinstance(rule.lineage, dict) else {}

    for src in (pv, lin):
        rrmap = src.get("rejection_reason_map")
        if isinstance(rrmap, dict):
            for k, v in rrmap.items():
                code = str(k).strip()
                if not code:
                    continue
                lab = str(v).strip() if v is not None else code
                out.append((code, lab[:512]))
        codes = src.get("rejection_codes")
        if isinstance(codes, list):
            for c in codes:
                s = str(c).strip()
                if s:
                    out.append((s, s))

    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for code, lab in out:
        if code in seen:
            continue
        seen.add(code)
        deduped.append((code, lab))
    return deduped


def ensure_rejection_reason_row(
    db: Session,
    code: str,
    label: str,
    *,
    apply: bool,
    scratch: Optional[dict[str, str]] = None,
) -> tuple[Optional[str], Optional[dict[str, Any]]]:
    row = (
        db.query(models.RejectionReason)
        .filter(models.RejectionReason.code == code)
        .first()
    )
    if row:
        return row.id, None
    plan = {"kind": "create_rejection_reason", "code": code, "label": label[:512]}
    if apply:
        rr = models.RejectionReason(code=code, label=label[:512], category="mapped")
        db.add(rr)
        db.flush()
        return rr.id, None

    assert scratch is not None
    if code in scratch:
        return scratch[code], None
    pending = f"__pending_rejection_reason__:{code}"
    scratch[code] = pending
    return pending, plan


def ensure_rejection_link(
    db: Session, rule_id: str, reason_id: str, *, apply: bool
) -> tuple[bool, Optional[dict[str, Any]]]:
    exists = (
        db.query(models.RuleRejectionLink)
        .filter(
            models.RuleRejectionLink.rule_id == rule_id,
            models.RuleRejectionLink.rejection_reason_id == reason_id,
        )
        .first()
    )
    if exists:
        return False, None
    plan = {
        "kind": "create_rule_rejection_link",
        "rule_id": rule_id,
        "rejection_reason_id": reason_id,
    }
    if not apply:
        return True, plan
    db.add(
        models.RuleRejectionLink(rule_id=rule_id, rejection_reason_id=reason_id)
    )
    return True, None


def backfill_jurisdictions(
    db: Session, *, dry_run: bool = True
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    apply = not dry_run
    changes: list[dict[str, Any]] = []
    updated = 0
    j_before = (
        db.query(func.count(models.Jurisdiction.id)).scalar()
        if apply
        else 0
    )
    jc_dry: set[str] = set()
    scratch: dict[str, str] = {}
    for rule in db.query(models.Rule).order_by(models.Rule.id).all():
        if rule.jurisdiction_id:
            continue
        code_eff = state_to_us_code(rule.state)
        jur_existed = bool(code_eff and find_jurisdiction_id_by_code(db, code_eff))
        jid, plan = ensure_jurisdiction_row(
            db, rule.state, apply=apply, scratch=None if apply else scratch
        )
        if plan:
            changes.append(plan)
            if dry_run and isinstance(plan.get("code"), str):
                jc_dry.add(plan["code"])
        if jid:
            changes.append(
                {
                    "kind": "set_jurisdiction_id",
                    "rule_id": rule.id,
                    "jurisdiction_id": jid,
                }
            )
            if apply:
                rule.jurisdiction_id = jid
                updated += 1
    jurisdictions_created = len(jc_dry) if dry_run else (
        int(
            db.query(func.count(models.Jurisdiction.id)).scalar() or 0
        )
        - int(j_before)
    )
    return changes, {"jurisdictions_updated": updated, "jurisdictions_created": jurisdictions_created}


def backfill_program_variants(
    db: Session, *, dry_run: bool = True
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    apply = not dry_run
    changes: list[dict[str, Any]] = []
    updated = 0
    pv_before = (
        db.query(func.count(models.ProgramVariantDef.id)).scalar()
        if apply
        else 0
    )
    pv_dry_slugs: set[str] = set()
    scratch: dict[str, str] = {}
    for rule in db.query(models.Rule).order_by(models.Rule.id).all():
        if rule.program_variant_ref_id:
            continue
        pv = rule.program_variant
        if not isinstance(pv, dict) or not pv:
            continue
        jid = rule.jurisdiction_id
        pvid, plans = ensure_program_variant_def_id(
            db,
            pv,
            jurisdiction_id=jid,
            apply=apply,
            scratch=None if apply else scratch,
        )
        for p in plans:
            changes.append(p)
            ks = p.get("key_slug")
            if isinstance(ks, str):
                pv_dry_slugs.add(ks)
        if pvid:
            changes.append(
                {
                    "kind": "set_program_variant_ref_id",
                    "rule_id": rule.id,
                    "program_variant_ref_id": pvid,
                }
            )
            if apply:
                rule.program_variant_ref_id = pvid
                updated += 1
    program_variants_created = len(pv_dry_slugs) if dry_run else (
        int(db.query(func.count(models.ProgramVariantDef.id)).scalar() or 0)
        - int(pv_before)
    )
    return changes, {
        "program_variants_updated": updated,
        "program_variants_created": program_variants_created,
    }


def backfill_rejection_links(
    db: Session, *, dry_run: bool = True
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    apply = not dry_run
    changes: list[dict[str, Any]] = []
    rr_before = int(db.query(func.count(models.RejectionReason.id)).scalar() or 0) if apply else 0
    lr_before = int(db.query(func.count(models.RuleRejectionLink.rule_id)).scalar() or 0) if apply else 0
    reason_scratch: dict[str, str] = {}
    for rule in db.query(models.Rule).order_by(models.Rule.id).all():
        pairs = _rejection_pairs_from_rule(rule)
        if not pairs:
            continue
        for code, label in pairs:
            rid, rplan = ensure_rejection_reason_row(
                db,
                code,
                label,
                apply=apply,
                scratch=None if apply else reason_scratch,
            )
            if rplan:
                changes.append(rplan)
            if not rid:
                continue
            _is_new, lplan = ensure_rejection_link(db, rule.id, rid, apply=apply)
            if lplan:
                changes.append(lplan)

    if apply:
        rr_after = int(db.query(func.count(models.RejectionReason.id)).scalar() or 0)
        lr_after = int(db.query(func.count(models.RuleRejectionLink.rule_id)).scalar() or 0)
        rejection_reasons_created = rr_after - rr_before
        rejection_links_created = lr_after - lr_before
    else:
        rejection_reasons_created = len(
            {c["code"] for c in changes if c.get("kind") == "create_rejection_reason"}
        )
        rejection_links_created = len(
            [c for c in changes if c.get("kind") == "create_rule_rejection_link"]
        )

    return changes, {
        "rejection_links_created": rejection_links_created,
        "rejection_reasons_created": rejection_reasons_created,
    }


def _rule_rejection_map_nonempty(rule: models.Rule) -> bool:
    pv = rule.program_variant if isinstance(rule.program_variant, dict) else {}
    lin = rule.lineage if isinstance(rule.lineage, dict) else {}
    for src in (pv, lin):
        m = src.get("rejection_reason_map")
        if isinstance(m, dict) and m:
            return True
    return False


def canonical_consistency_report(db: Session) -> dict[str, Any]:
    rules = db.query(models.Rule).all()
    total = len(rules)
    missing_j = sum(1 for r in rules if not r.jurisdiction_id)
    missing_pv = sum(1 for r in rules if not r.program_variant_ref_id)
    legacy_pv_no_fk = sum(
        1
        for r in rules
        if bool(r.program_variant) and not r.program_variant_ref_id
    )
    rej_map_no_links = 0
    for r in rules:
        if not _rule_rejection_map_nonempty(r):
            continue
        nlink = (
            db.query(models.RuleRejectionLink)
            .filter(models.RuleRejectionLink.rule_id == r.id)
            .count()
        )
        if nlink == 0:
            rej_map_no_links += 1

    by_status = Counter(r.review_status for r in rules)
    by_tenant = Counter(r.tenant_id for r in rules)

    return {
        "total_rules": total,
        "rules_missing_jurisdiction_id": missing_j,
        "rules_missing_program_variant_ref_id": missing_pv,
        "rules_with_legacy_program_variant_but_no_fk": legacy_pv_no_fk,
        "rules_with_rejection_map_but_no_links": rej_map_no_links,
        "rules_by_review_status": dict(sorted(by_status.items())),
        "rules_by_tenant_id": dict(sorted(by_tenant.items())),
    }


def run_backfill(
    db: Session, *, target: Target, dry_run: bool = True
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Run one or all backfill targets; caller commits when dry_run is False."""
    all_changes: list[dict[str, Any]] = []
    summary: dict[str, int] = {}
    if target in ("all", "jurisdictions"):
        ch, sm = backfill_jurisdictions(db, dry_run=dry_run)
        all_changes.extend(ch)
        summary.update(sm)
    if target in ("all", "program_variants"):
        ch, sm = backfill_program_variants(db, dry_run=dry_run)
        all_changes.extend(ch)
        summary.update(sm)
    if target in ("all", "rejection_links"):
        ch, sm = backfill_rejection_links(db, dry_run=dry_run)
        all_changes.extend(ch)
        summary.update(sm)
    return all_changes, summary


def sync_canonical_fields_for_new_rule(db: Session, rule: models.Rule) -> None:
    """Forward-fill FKs after rule insert; does not clear legacy JSON; idempotent."""
    if not rule.jurisdiction_id:
        jid, _ = ensure_jurisdiction_row(db, rule.state, apply=True, scratch=None)
        if jid:
            rule.jurisdiction_id = jid

    pv = rule.program_variant if isinstance(rule.program_variant, dict) else None
    if pv and not rule.program_variant_ref_id:
        pvid, _ = ensure_program_variant_def_id(
            db,
            pv,
            jurisdiction_id=rule.jurisdiction_id,
            apply=True,
            scratch=None,
        )
        if pvid:
            rule.program_variant_ref_id = pvid

    pairs = _rejection_pairs_from_rule(rule)
    for code, label in pairs:
        rid, _ = ensure_rejection_reason_row(db, code, label, apply=True, scratch=None)
        if not rid:
            continue
        ensure_rejection_link(db, rule.id, rid, apply=True)
