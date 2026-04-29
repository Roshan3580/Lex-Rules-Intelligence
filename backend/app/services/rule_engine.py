"""Deterministic rule execution for submission enforcement (no LLM).

Maps to Engineer Brief §4.3–§4.4: pre-submission gates and explainable
decisions. Only ``published`` and ``approved`` rules participate.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy.orm import Session

from .. import models
from .cache_service import (
    DEFAULT_TTL_RULE_LOOKUP,
    DEFAULT_TTL_VALIDATION,
    NAMESPACE_RULE_LOOKUP,
    NAMESPACE_VALIDATION,
    default_cache,
    make_key,
    sha256_hex,
    stable_canonical_json,
)
from .validation import MIN_PUBLISH_CONFIDENCE

ENFORCEMENT_STATUSES = frozenset({"published", "approved"})

# USPS abbreviation → full state name (subset; extend as needed)
_STATE_ABBR: dict[str, str] = {
    "AL": "Alabama",
    "AK": "Alaska",
    "AZ": "Arizona",
    "AR": "Arkansas",
    "CA": "California",
    "CO": "Colorado",
    "CT": "Connecticut",
    "DE": "Delaware",
    "FL": "Florida",
    "GA": "Georgia",
    "HI": "Hawaii",
    "ID": "Idaho",
    "IL": "Illinois",
    "IN": "Indiana",
    "IA": "Iowa",
    "KS": "Kansas",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "ME": "Maine",
    "MD": "Maryland",
    "MA": "Massachusetts",
    "MI": "Michigan",
    "MN": "Minnesota",
    "MS": "Mississippi",
    "MO": "Missouri",
    "MT": "Montana",
    "NE": "Nebraska",
    "NV": "Nevada",
    "NH": "New Hampshire",
    "NJ": "New Jersey",
    "NM": "New Mexico",
    "NY": "New York",
    "NC": "North Carolina",
    "ND": "North Dakota",
    "OH": "Ohio",
    "OK": "Oklahoma",
    "OR": "Oregon",
    "PA": "Pennsylvania",
    "RI": "Rhode Island",
    "SC": "South Carolina",
    "SD": "South Dakota",
    "TN": "Tennessee",
    "TX": "Texas",
    "UT": "Utah",
    "VT": "Vermont",
    "VA": "Virginia",
    "WA": "Washington",
    "WV": "West Virginia",
    "WI": "Wisconsin",
    "WY": "Wyoming",
}


def normalize_state(state: Optional[str]) -> str:
    if not state:
        return ""
    s = state.strip()
    if len(s) == 2:
        return _STATE_ABBR.get(s.upper(), s)
    return s


def _wants_condition_eval(raw: Any) -> bool:
    """True if condition_logic is non-empty and should be parsed/evaluated."""
    if raw is None:
        return False
    if isinstance(raw, str):
        return bool(raw.strip())
    if isinstance(raw, dict):
        return len(raw) > 0
    return True


def _parse_condition_logic(raw: Any) -> Optional[dict[str, Any]]:
    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        t = raw.strip()
        if not t:
            return None
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            return None
    return None


def _payload_get(payload: dict[str, Any], field: str) -> Any:
    if "." in field:
        base, _, rest = field.partition(".")
        sub = payload.get(base)
        if isinstance(sub, dict):
            return sub.get(rest)
        return None
    return payload.get(field)


def _norm_token(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def _doc_tokens(payload: dict[str, Any]) -> set[str]:
    """Flatten documents + forms strings from payload for fuzzy includes."""
    raw: list[Any] = []
    for key in ("documents", "forms", "attachments"):
        v = payload.get(key)
        if isinstance(v, list):
            raw.extend(v)
        elif isinstance(v, str) and v.strip():
            raw.extend(x.strip() for x in v.split(",") if x.strip())
    return {_norm_token(str(x)) for x in raw if str(x).strip()}


def _item_matches_submission(item: str, doc_tokens: set[str]) -> bool:
    """True if normalized item appears in any document token (substring)."""
    n = _norm_token(item)
    if not n:
        return False
    if n in doc_tokens:
        return True
    for t in doc_tokens:
        if n in t or t in n:
            return True
    return False


def _compare(op: str, left: Any, right: Any) -> bool:
    try:
        if op == "equals":
            return left == right or str(left).strip() == str(right).strip()
        if op == "not_equals":
            return not (left == right or str(left).strip() == str(right).strip())
        if op in ("greater_than", "less_than", "greater_or_equal", "less_or_equal"):
            lf = float(left) if left is not None else None
            rt = float(right) if right is not None else None
            if lf is None or rt is None:
                return False
            if op == "greater_than":
                return lf > rt
            if op == "less_than":
                return lf < rt
            if op == "greater_or_equal":
                return lf >= rt
            return lf <= rt
        if op == "includes":
            if left is None:
                return False
            if isinstance(left, list):
                return str(right) in [str(x) for x in left]
            if isinstance(left, str):
                return str(right).lower() in left.lower()
            return False
        if op == "exists":
            return left is not None and left != ""
        if op == "missing":
            return left is None or left == ""
    except (TypeError, ValueError):
        return False
    return False


def evaluate_condition_logic(
    node: Any,
    payload: dict[str, Any],
) -> tuple[bool, list[str], list[str]]:
    """Evaluate a condition node; return (pass, met_msgs, failed_msgs)."""
    met: list[str] = []
    failed: list[str] = []

    if node is None:
        return True, ["(no condition — applies)"], []

    if not isinstance(node, dict):
        return True, [], [f"(ignored non-object condition: {type(node).__name__})"]

    op = (node.get("op") or node.get("operator") or "").strip().lower()

    if op in ("and", "all"):
        items = node.get("items") or node.get("args") or []
        if not isinstance(items, list):
            return False, [], ["and: invalid items"]
        all_ok = True
        for i, sub in enumerate(items):
            ok, sm, sf = evaluate_condition_logic(sub, payload)
            met.extend([f"[and {i}] {m}" for m in sm])
            failed.extend([f"[and {i}] {f}" for f in sf])
            if not ok:
                all_ok = False
        return all_ok, met, failed

    if op in ("or", "any"):
        items = node.get("items") or node.get("args") or []
        if not isinstance(items, list):
            return False, [], ["or: invalid items"]
        any_ok = False
        for i, sub in enumerate(items):
            ok, sm, sf = evaluate_condition_logic(sub, payload)
            met.extend(sm)
            failed.extend(sf)
            if ok:
                any_ok = True
        return any_ok, met, failed

    fld = node.get("field") or node.get("left")
    val = node.get("value") or node.get("right")
    left = _payload_get(payload, fld) if fld else None

    if op == "equals":
        ok = _compare("equals", left, val)
    elif op == "not_equals":
        ok = _compare("not_equals", left, val)
    elif op == "greater_than":
        ok = _compare("greater_than", left, val)
    elif op == "less_than":
        ok = _compare("less_than", left, val)
    elif op == "greater_or_equal":
        ok = _compare("greater_or_equal", left, val)
    elif op == "less_or_equal":
        ok = _compare("less_or_equal", left, val)
    elif op == "includes":
        ok = _compare("includes", left, val)
    elif op == "exists":
        ok = _compare("exists", left, None)
    elif op == "missing":
        ok = _compare("missing", left, None)
    else:
        return False, [], [f"unknown operator: {op!r}"]

    msg = f"{op} {fld!r} vs {val!r}"
    if ok:
        met.append(msg)
    else:
        failed.append(msg)
    return ok, met, failed


def _effective_applies(
    rule: models.Rule,
    as_of: Optional[str],
) -> bool:
    """Coarse string/date comparison for effective range."""
    if not as_of:
        return True
    ad = _parse_loose_date(as_of)
    if ad is None:
        return True
    start = _parse_loose_date(rule.effective_date)
    end = _parse_loose_date(rule.effective_date_end)
    if start and ad < start:
        return False
    if end and ad > end:
        return False
    return True


def _parse_loose_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = str(s).strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(s[:10].replace("T", " ")[:10], fmt.replace("T%H:%M:%S", "")).date()
        except ValueError:
            continue
    try:
        if len(s) == 4 and s.isdigit():
            return date(int(s), 1, 1)
    except ValueError:
        pass
    return None


def _program_variant_matches(
    rule_pv: Optional[dict[str, Any]],
    request_pv: Optional[dict[str, Any]],
) -> bool:
    if not request_pv:
        return True
    if not rule_pv:
        return True
    for k, v in request_pv.items():
        if rule_pv.get(k) != v:
            return False
    return True


def _rules_ordered_by_ids(
    db: Session,
    tenant_id: str,
    ids: list[str],
) -> list[models.Rule]:
    if not ids:
        return []
    rows = (
        db.query(models.Rule)
        .filter(models.Rule.id.in_(ids))
        .filter(models.Rule.tenant_id == tenant_id)
        .all()
    )
    by_id = {r.id: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]


def _rule_lookup_cache_key(
    *,
    tenant_id: str,
    state: str,
    tax_category: str,
    workflow_stage: Optional[str],
    effective_date: Optional[str],
    program_variant: Optional[dict[str, Any]],
) -> str:
    pv_digest = sha256_hex(
        stable_canonical_json(
            program_variant if program_variant is not None else None
        )
    )
    blob = stable_canonical_json(
        {
            "tenant_id": tenant_id,
            "state": normalize_state(state),
            "tax_category": tax_category,
            "workflow_stage": workflow_stage or "",
            "effective_date": effective_date or "",
            "program_variant_digest": pv_digest,
        }
    )
    return make_key(NAMESPACE_RULE_LOOKUP, sha256_hex(blob))


def _validation_cache_key(
    tenant_id: str,
    state: str,
    tax_category: str,
    workflow_stage: Optional[str],
    effective_date: Optional[str],
    program_variant: Optional[dict[str, Any]],
    payload: dict[str, Any],
) -> str:
    blob = stable_canonical_json(
        {
            "tenant_id": tenant_id,
            "state": normalize_state(state),
            "tax_category": tax_category,
            "workflow_stage": workflow_stage or "",
            "effective_date": effective_date or "",
            "program_variant": program_variant if program_variant is not None else None,
            "payload_digest": sha256_hex(stable_canonical_json(payload)),
        }
    )
    return make_key(NAMESPACE_VALIDATION, sha256_hex(blob))


def get_applicable_rules(
    db: Session,
    *,
    tenant_id: str = "default",
    state: str,
    tax_category: str,
    workflow_stage: Optional[str] = None,
    effective_date: Optional[str] = None,
    program_variant: Optional[dict[str, Any]] = None,
) -> tuple[list[models.Rule], list[str]]:
    """Return enforcement-eligible rules matching filters + effective dates."""
    cache = default_cache()
    ck = _rule_lookup_cache_key(
        tenant_id=tenant_id,
        state=state,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        effective_date=effective_date,
        program_variant=program_variant,
    )
    cached_pair = cache.get(ck)
    if cached_pair is not None:
        ids, cached_warnings = cached_pair
        hydrated = _rules_ordered_by_ids(db, tenant_id, ids)
        if len(hydrated) == len(ids):
            return hydrated, cached_warnings
        cache.delete(ck)

    warnings: list[str] = []
    st = normalize_state(state)
    q = (
        db.query(models.Rule)
        .filter(models.Rule.tenant_id == tenant_id)
        .filter(models.Rule.state == st)
        .filter(models.Rule.tax_category == tax_category)
        .filter(models.Rule.review_status.in_(ENFORCEMENT_STATUSES))
    )
    if workflow_stage:
        q = q.filter(
            (models.Rule.workflow_stage == workflow_stage)
            | (models.Rule.workflow_stage.is_(None))
        )
    rules = q.order_by(models.Rule.confidence_score.desc()).all()
    out: list[models.Rule] = []
    for r in rules:
        if not _effective_applies(r, effective_date):
            continue
        if not _program_variant_matches(r.program_variant, program_variant):
            continue
        raw = r.condition_logic
        node = _parse_condition_logic(raw)
        if isinstance(node, dict) and len(node) == 0:
            node = None

        if _wants_condition_eval(raw) and node is None:
            warnings.append(
                f"rule {r.id}: malformed condition_logic skipped for evaluation"
            )
            continue
        out.append(r)
    ids_snapshot = [r.id for r in out]
    cache.set(ck, (ids_snapshot, warnings), DEFAULT_TTL_RULE_LOOKUP)
    return out, warnings


@dataclass
class RuleEvalDetail:
    rule_id: str
    rule_title: str
    applied: bool
    conditions_met: list[str] = field(default_factory=list)
    conditions_failed: list[str] = field(default_factory=list)
    missing_forms: list[str] = field(default_factory=list)
    missing_docs: list[str] = field(default_factory=list)
    missing_actions: list[str] = field(default_factory=list)
    confidence: float = 0.0
    source_id: Optional[str] = None
    source_url: Optional[str] = None
    snippet: Optional[str] = None
    skip_reason: Optional[str] = None


def evaluate_rule(
    rule: models.Rule,
    payload: dict[str, Any],
    *,
    as_of_date: Optional[str] = None,
) -> RuleEvalDetail:
    """Evaluate one rule: condition tree + required artifacts vs payload."""
    detail = RuleEvalDetail(
        rule_id=rule.id,
        rule_title=rule.rule_title,
        applied=False,
        confidence=float(rule.confidence_score or 0),
        source_id=rule.source_id,
        source_url=rule.source_url,
        snippet=(rule.source_snippet or "")[:500] or None,
    )
    if not _effective_applies(rule, as_of_date):
        detail.skip_reason = "outside effective date range"
        return detail

    node = _parse_condition_logic(rule.condition_logic)
    if isinstance(node, dict) and len(node) == 0:
        node = None

    if _wants_condition_eval(rule.condition_logic) and node is None:
        detail.skip_reason = "malformed condition_logic"
        detail.conditions_failed.append("could not parse condition_logic JSON")
        return detail
    if node is not None:
        ok, met, failed = evaluate_condition_logic(node, payload)
        detail.conditions_met = met
        detail.conditions_failed = failed
        if not ok:
            detail.skip_reason = "conditions not met"
            return detail
    else:
        detail.conditions_met = ["(no condition — applies when filters match)"]

    detail.applied = True
    return detail


def _collect_violations_for_applied_rule(
    rule: models.Rule,
    payload: dict[str, Any],
    detail: RuleEvalDetail,
) -> None:
    docs = _doc_tokens(payload)

    for form in rule.required_forms or []:
        if not form or not str(form).strip():
            continue
        if not _item_matches_submission(str(form), docs):
            detail.missing_forms.append(str(form))

    for doc in rule.required_documentation or []:
        if not doc or not str(doc).strip():
            continue
        if not _item_matches_submission(str(doc), docs):
            detail.missing_docs.append(str(doc))

    # required_actions: treat each as a phrase that should appear in payload "actions_done" list or in documents
    actions_done: set[str] = set()
    ad = payload.get("actions_done")
    if isinstance(ad, list):
        actions_done = {_norm_token(str(x)) for x in ad}
    combined = docs | actions_done

    for act in rule.required_actions or []:
        if not act or not str(act).strip():
            continue
        if not _item_matches_submission(str(act), combined):
            detail.missing_actions.append(str(act))


def validate_submission(
    db: Session,
    *,
    tenant_id: str = "default",
    state: str,
    tax_category: str,
    workflow_stage: Optional[str] = None,
    effective_date: Optional[str] = None,
    program_variant: Optional[dict[str, Any]] = None,
    payload: dict[str, Any],
    debug: bool = False,
) -> dict[str, Any]:
    """Full submission validation — deterministic, explainable."""
    cache = default_cache()
    vk: Optional[str] = None
    if not debug:
        vk = _validation_cache_key(
            tenant_id,
            state,
            tax_category,
            workflow_stage,
            effective_date,
            program_variant,
            payload,
        )
        hit = cache.get(vk)
        if hit is not None:
            return hit

    warnings: list[str] = []
    violations: list[dict[str, Any]] = []
    passed_rules: list[dict[str, str]] = []
    rule_warnings: list[str] = []

    rules, w0 = get_applicable_rules(
        db,
        tenant_id=tenant_id,
        state=state,
        tax_category=tax_category,
        workflow_stage=workflow_stage,
        effective_date=effective_date,
        program_variant=program_variant,
    )
    warnings.extend(w0)

    for rule in rules:
        if rule.confidence_score < MIN_PUBLISH_CONFIDENCE:
            rule_warnings.append(
                f"Rule {rule.id} has confidence {rule.confidence_score:.2f} "
                f"below publish threshold {MIN_PUBLISH_CONFIDENCE:.2f} — verify manually."
            )

        ev = evaluate_rule(rule, payload, as_of_date=effective_date)
        if not ev.applied:
            continue

        _collect_violations_for_applied_rule(rule, payload, ev)

        if ev.missing_forms or ev.missing_docs or ev.missing_actions:
            parts = []
            if ev.missing_forms:
                parts.append("Missing forms: " + ", ".join(ev.missing_forms))
            if ev.missing_docs:
                parts.append("Missing documentation: " + ", ".join(ev.missing_docs))
            if ev.missing_actions:
                parts.append("Missing actions: " + ", ".join(ev.missing_actions))
            reason = "; ".join(parts)
            req_action = (
                (rule.required_actions[0] if rule.required_actions else None)
                or f"Provide: {', '.join(ev.missing_forms + ev.missing_docs + ev.missing_actions)}"
            )
            violations.append(
                {
                    "rule_id": rule.id,
                    "rule_title": rule.rule_title,
                    "reason": reason,
                    "required_action": req_action,
                    "required_documentation": ev.missing_docs + ev.missing_forms,
                    "confidence": float(rule.confidence_score or 0),
                    "source": {
                        "source_id": rule.source_id,
                        "source_url": rule.source_url,
                        "snippet": (rule.source_snippet or "")[:1200] or None,
                    },
                    "conditions_met": ev.conditions_met,
                    "conditions_failed": ev.conditions_failed,
                }
            )
        else:
            passed_rules.append({"rule_id": rule.id, "rule_title": rule.rule_title})

    valid = len(violations) == 0
    if violations:
        risk = "high"
    elif rule_warnings:
        risk = "medium"
    else:
        risk = "low"

    expl = (
        "Submission blocked because one or more enforced rules are not satisfied."
        if violations
        else (
            "Submission cleared — no blocking violations against published/approved rules."
            if not rule_warnings
            else "Submission cleared with warnings — review low-confidence rules."
        )
    )

    result = {
        "valid": valid,
        "risk_level": risk,
        "violations": violations,
        "warnings": warnings + rule_warnings,
        "passed_rules": passed_rules,
        "explanation": expl,
    }

    if (
        not debug
        and vk is not None
        and not any("malformed condition_logic" in w for w in w0)
    ):
        cache.set(vk, result, DEFAULT_TTL_VALIDATION)

    return result
