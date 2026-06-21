# Human Review Workflow

## Why human review exists

Tax and compliance rules are high-stakes. Automated extraction and retrieval can be wrong, incomplete, or mis-scoped. Lex routes uncertain outputs to reviewers before they become operational truth.

Human review complements—not replaces—source grounding and confidence scoring.

## Review states

Defined in `backend/app/schemas.py` as `REVIEW_STATUSES`:

| Status | Meaning |
| --- | --- |
| `draft` | Newly extracted; not validated for use |
| `auto_validated` | Passed automated validation signals; still reviewable |
| `needs_review` | Flagged for explicit human attention |
| `approved` | Reviewer approved; eligible for publish (with gates) |
| `published` | Available for enforcement / boosted retrieval |
| `rejected` | Reviewer rejected; not for operational use |

The review **queue** (`GET /api/review/queue`) returns rules in `draft`, `needs_review`, or `auto_validated`.

## Review queue

The Review Queue UI (`/app/review`) shows:

- Pending rules with title, source document, confidence, and status
- Detail pane with extracted fields, source snippet, and program metadata
- Version history (`GET /api/rules/{id}/versions`)
- Publish readiness check (`GET /api/rules/{id}/publish-readiness`)

Demo mode seeds illustrative queue items across CA, TX, and NY when `DEMO_MODE=true`.

## Reviewer actions

Supported via `POST /api/review/rules/{id}/action`:

| Action | Effect |
| --- | --- |
| `edit` | Update rule fields (creates review event) |
| `approve` | Sets status to `approved` |
| `reject` | Sets status to `rejected` |
| `publish` | Sets status to `published` (gated—see below) |
| `needs_review` | Sends rule back to review |

Rule field updates also available via `PATCH /api/review/rules/{id}`.

### Publish gates

Publishing requires (enforced in `review_service` / `validation.py`):

- Prior **approval**
- Passing validation checks
- Confidence at or above the configured publish threshold (0.70 in code)

Failed publish attempts return blockers; the UI can call publish-readiness to inspect them.

## Auditability

Every review action creates a `ReviewEvent` with actor, action, timestamp, and diff metadata.

Additional audit surfaces:

- `GET /api/review/rules/{id}/events` — per-rule history
- `GET /api/audit` — platform audit log
- `GET /api/admin/audit` — admin audit feed

Ingestion runs and monitor jobs provide separate operational history.

## Trust model

Trust comes from layering:

1. **Source evidence** — snippet, URL, document name, checksum, `last_checked`
2. **Confidence scores** — extraction and answer-level signals
3. **Reviewer decisions** — explicit approve / reject / publish with audit trail
4. **Deterministic enforcement** — submission validation uses published/approved rules only (no LLM)

## Limitations

- Human review improves reliability but does **not** certify legal or tax correctness.
- Reviewers still need domain expertise and authoritative primary sources.
- Demo seed rules are **illustrative**—not regulator-approved guidance.
- RBAC in the UI is a prototype role switcher, not production SSO or multi-tenant security.
