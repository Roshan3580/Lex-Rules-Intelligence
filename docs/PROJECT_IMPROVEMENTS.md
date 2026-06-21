# Project Improvements

## Current strengths

- Polished editorial landing page and consistent light app shell
- End-to-end demo path: ingest → search → review → analytics
- Source ingestion (PDF, URL, text, YAML batch)
- Rule Search with citations, confidence, and fallback answers
- Human review queue with approve / reject / publish
- Dashboard KPIs and activity feed
- Analytics and rejection coverage surfaces
- Deterministic submission validator (no LLM)
- Docker Compose for local containerized runs
- Backend test suite (`pytest`)

## Completed polish

- Portfolio screenshots in `screenshots/`
- Frontend restyled to match landing page design language
- README rewritten for recruiters and hiring managers
- Architecture, RAG, review, and improvements docs added
- Demo mode seed for Rule Search and Review Queue demos

## Remaining improvements

### P0 — before public release

- **Review potentially sensitive references** — code comments and YAML headers mention an external engineering brief; README no longer references private PDFs, but grep for brief/stealth/company names before publishing
- **Review personal contact info** — landing page includes a contact email; confirm it should be public
- **Verify screenshot links** — confirm images render on GitHub (case-sensitive paths)
- **Verify doc links** — README → `docs/*.md` relative links
- **Confirm `.env` / `rules.db` are gitignored** — they are; do not commit secrets or local DB

### P1 — portfolio impact

- Deploy a public read-only demo (Render, Fly.io, etc.) with `DEMO_MODE=true`
- Record a short Loom walkthrough (ingest → search → review)
- Expand frontend tests beyond the example stub
- Document demo reset (`POST /api/demo/reset`) for evaluators
- Mobile sidebar navigation (currently hidden below `lg`)

### P2 — product hardening

- Production auth (OIDC/SSO) instead of demo RBAC switcher
- Observability (structured logging, metrics, tracing)
- Background job queue for long batch ingests
- Managed vector store (pgvector, Qdrant) at scale
- Playwright-based ingestion for JS-heavy regulator portals
- Golden-set eval harness for retrieval quality
- Multi-tenant row-level security

## Resume bullets

Use as starting points—adjust to your voice:

- Built a **source-backed rules intelligence platform** that ingests PDFs, URLs, and pasted text, extracts structured tax rules, and returns cited answers with confidence scores and human review gates.
- Designed **ingestion → retrieval → answer → review** workflows in FastAPI and React, including deterministic fallback when no LLM key is configured and a governed publish pipeline with audit events.
- Implemented **hybrid retrieval, citation tracking, and review-queue UX** to demonstrate human-in-the-loop compliance tooling rather than an unconstrained chatbot wrapper.

## Interview stories

This project supports discussing:

| Topic | Angle |
| --- | --- |
| RAG vs chatbot wrapper | Citations, rules_used, evidence sufficiency, fallback when retrieval is empty |
| Source grounding | Checksums, snippets, last_checked, source chunks vs invented answers |
| Human-in-the-loop | Review statuses, publish gates, ReviewEvent audit trail |
| Ingestion pipeline | PDF/HTML parsing, dedupe, monitor/re-ingest on change |
| Confidence scoring | Extraction validation, answer downgrade, UI surfacing |
| Prototype tradeoffs | SQLite + modular monolith, hash embeddings, demo seed vs real corpus |
| Deterministic enforcement | validate-submission without LLM; separation from generative Q&A |
