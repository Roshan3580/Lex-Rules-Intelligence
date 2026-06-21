# State Tax Rules Intelligence Platform

A production-style prototype that turns fragmented state tax law sources
(state department websites, PDFs, bulletins, manuals, uploaded documents,
pasted text) into structured, searchable, source-backed workflow
intelligence — for all 50 U.S. states.

It is **not** a chatbot wrapper. Every answer is grounded in indexed
sources, returns citations and a confidence score, and routes
low-confidence rules to a human review console. The data model and
ingestion pipeline are inspired directly by the canonical rule schema in
the engineering brief (`Product Overview - Derrick Lewis - Stealth Startup
- v2.pdf`).

> **Design principle:** "Turn fragmented state tax law sources into
> structured, searchable, source-backed workflow intelligence."

---

## What it does

Users can ask questions like:

- *"What are the sales tax filing requirements in California?"*
- *"What payroll tax rules apply in Texas?"*
- *"What forms are required for New York employer withholding?"*
- *"What are the filing deadlines for Florida corporate tax?"*

For each question the platform:

1. Filters by **state** and **tax type** (if provided).
2. Retrieves relevant **rules** and **source chunks**.
3. Generates a grounded answer (LLM if configured, otherwise a
   deterministic fallback that summarizes the top-ranked rules).
4. Returns **citations**, a **confidence score**, the **rules used**,
   and the **last_checked** timestamp for each source so the user can
   verify everything against the original document or webpage.

It also lets operators **upload PDFs, ingest URLs, paste text, or run a
curated batch** (`app/data/sources.yaml`) and auto-extracts candidate
rules. Anything below a confidence threshold is routed to an **admin
review queue** for edit / approve / publish / reject actions, with a
full audit trail.

## Tech stack

- **Backend:** Python 3.11 · FastAPI · SQLAlchemy 2.x · Pydantic v2
- **DB:** SQLite by default; PostgreSQL via `DATABASE_URL`
  (compose has an optional `postgres` profile)
- **Ingestion:** `requests` + `BeautifulSoup` for HTML; PyMuPDF →
  pdfplumber fallback for PDFs
- **LLM:** any OpenAI-compatible chat-completions endpoint (configurable
  via `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_MODEL`); deterministic
  fallback when no key is set
- **Frontend:** React 18 + TypeScript + Vite + Tailwind + shadcn/ui +
  TanStack Query (wired to the backend)

## Architecture

This is a **modular monolith**. Single deployable, clear module
boundaries:

```
┌──────────────────────────────┐         ┌────────────────────────────────────────┐
│  React + TS + Tailwind UI    │  /api   │  FastAPI                               │
│  /app/search   (Rule Search) │ ──────▶ │  routers/ → services/ → models         │
│  /app/sources  (Sources)     │         │                                        │
│  /app/review   (Review)      │         │  meta · sources · rules · questions    │
│  /app                        │         │  · review · ingest · monitor          │
└──────────────────────────────┘         │                                        │
                                         │  ingestion → extraction →              │
                                         │  retrieval → answer → review           │
                                         │                                        │
                                         │  Source · SourceChunk · Rule           │
                                         │  Question · Answer · ReviewEvent       │
                                         └─────────────────┬──────────────────────┘
                                                           │
                                                ┌──────────▼──────────┐
                                                │ SQLite (default)    │
                                                │ or PostgreSQL       │
                                                └─────────────────────┘
```

```
backend/
  app/
    main.py                       # FastAPI app + startup (init DB, seed demo)
    config.py                     # Settings (env-driven, OpenAI-compat LLM)
    database.py                   # SQLAlchemy engine + session
    models.py                     # Source, SourceChunk, Rule, Question,
                                  # Answer, ReviewEvent (+ checksum,
                                  # last_checked, rule_category, page_number)
    schemas.py                    # Pydantic DTOs (incl. /api/query shape)
    seed.py                       # CA / TX / NY in-memory seed
    data/sources.yaml             # Curated state tax URLs for /api/ingest/run
    routers/
      meta.py                     # GET /health, GET /api/states
      sources.py                  # /api/sources/upload, /url, /text
      rules.py                    # GET /api/rules?state=&tax_type=
      questions.py                # POST /api/ask + POST /api/query
      review.py                   # /api/review/queue, edit, action, events
      validation.py               # /api/validate-submission, /api/outcomes
      ingest.py                   # POST /api/ingest/source, /api/ingest/run
      monitor.py                  # POST /api/monitor/run (checksum / refresh)
    services/
      ingestion_service.py        # PDF + URL + text + uploads → chunks
                                  # checksum-based dedupe, last_checked
      extraction_service.py       # Hybrid LLM + heuristic rule extraction
      retrieval_service.py        # Lexical retrieval over rules + chunks
      answer_service.py           # RAG flow: retrieve → answer → cite
      review_service.py           # Edit / approve / reject / publish + audit
      rule_engine.py              # Deterministic validate_submission (no LLM)
      outcomes_service.py         # Outcome events + rejection coverage
      seed_runner.py              # Loads sources.yaml and ingests each entry
      monitor_service.py          # Batch refresh + IngestionRun(kind=monitor)
    utils/
      chunking.py                 # Sentence-aware text chunker
      llm_client.py               # OpenAI-compatible HTTP client + JSON parser
  requirements.txt
  .env.example
  Dockerfile

frontend/
  src/
    lib/api.ts                    # Typed fetch client (states, query, ingest, …)
    pages/app/
      Dashboard.tsx               # Live KPIs from the backend
      RuleSearch.tsx              # Connected to POST /api/query
      Sources.tsx                 # Connected to /api/sources + /api/ingest
      ReviewQueue.tsx             # Connected to /api/review/*
      SubmissionValidator.tsx     # /app/validate — enforcement demo
      Outcomes.tsx                # /app/outcomes — feedback loop + coverage
      Workflows.tsx, Analytics.tsx, Admin.tsx
    components/                   # shadcn/ui + custom (Confidence, NavLink, …)
  vite.config.ts                  # /api + /health proxy → http://localhost:8000
  package.json

docker-compose.yml                # backend + frontend (+ optional postgres)
```

## API surface

| Method | Path                                    | Purpose                                           |
| ------ | --------------------------------------- | ------------------------------------------------- |
| GET    | `/health`                               | Backend status + LLM mode + DB type               |
| GET    | `/api/states`                           | All 50 U.S. states (name + abbreviation)          |
| GET    | `/api/rules`                            | Structured rules; `tax_type` synonym of `tax_category`; optional `workflow_stage` |
| POST   | `/api/query`                            | RAG Q&A · spec-shaped response with citations     |
| POST   | `/api/ingest/source`                    | Add one source (URL or pasted text)               |
| POST   | `/api/ingest/run`                       | Batch-run the curated `sources.yaml` list         |
| POST   | `/api/monitor/run`                      | Re-check sources: URL fetch + checksum; re-ingest on change |
| GET    | `/api/sources`                          | List indexed sources                              |
| POST   | `/api/sources/upload`                   | Multipart PDF/TXT/HTML upload                     |
| DELETE | `/api/sources/{id}`                     | Remove a source                                   |
| GET    | `/api/review/queue`                     | Rules needing human review                        |
| POST   | `/api/review/rules/{id}/action`         | approve / reject / publish / needs_review         |
| GET    | `/api/review/rules/{id}/events`         | Audit trail                                       |
| POST   | `/api/validate-submission`              | Deterministic enforcement: published/approved rules only; no LLM |
| POST   | `/api/outcomes`                          | Store rejection/outcome + coverage classification |
| GET    | `/api/outcomes`                          | List outcomes (`state`, `tax_category`, `coverage_status`) |
| GET    | `/api/analytics/rejection-coverage`     | Aggregate coverage %, buckets, top reasons      |

`POST /api/query` request:

```json
{
  "question": "What are the sales tax filing rules in California?",
  "state": "California",
  "tax_type": "sales_tax"
}
```

Response:

```json
{
  "answer": "...detailed answer grounded in retrieved sources...",
  "state": "California",
  "tax_type": "sales_tax",
  "confidence": 0.82,
  "method": "fallback",
  "sources": [
    {
      "title": "CDTFA — Sales and Use Tax in California",
      "url": "https://www.cdtfa.ca.gov/...",
      "snippet": "...",
      "document_type": "webpage",
      "last_checked": "2026-04-27T20:35:00Z",
      "state": "California",
      "tax_type": "sales_tax",
      "relevance": 0.41
    }
  ],
  "rules_used": [ /* full Rule objects */ ],
  "question_id": "…",
  "answered_at": "2026-04-27T20:35:00Z"
}
```

## Setup

### Prerequisites

- Python 3.11+
- Node 20+
- (Optional) Docker

### Environment variables

`backend/.env.example` shows the full set:

| Var               | Default                      | Notes                                 |
| ----------------- | ---------------------------- | ------------------------------------- |
| `DATABASE_URL`    | `sqlite:///./rules.db`       | Set Postgres URL to switch DBs        |
| `LLM_API_KEY`     | *(empty)*                    | If empty, deterministic fallback only |
| `LLM_BASE_URL`    | `https://api.openai.com/v1`  | Any OpenAI-compatible endpoint        |
| `LLM_MODEL`       | `gpt-4o-mini`                | Model name for extraction + answers   |
| `FRONTEND_ORIGIN` | `http://localhost:8080`      | CORS allowlist                        |
| `UPLOAD_DIR`      | `./uploads`                  | Where uploaded files are written      |

Copy and edit:

```bash
cp backend/.env.example backend/.env
```

### Run the backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

On first start the app:

1. Creates SQLite tables.
2. Seeds in-memory demo rules for **California, Texas, and New York**
   (so `/api/query` returns grounded answers immediately, even without
   running any external ingestion).

OpenAPI docs: <http://localhost:8000/docs>

### Submission validation & outcomes

Deterministic **`POST /api/validate-submission`** evaluates **published** and **approved** rules only (no LLM). The UI lives at **`/app/validate`**; rejection analytics and **`POST /api/outcomes`** are at **`/app/outcomes`**.

**Demo data:** With an **empty** `rules` table and **`DEMO_MODE=true`** in `backend/.env`, startup seeds CA / TX / NY rules plus two **California `sales_tax` / `submission`** enforcement examples (`CDTFA-401-A` documentation gate and an **LLC + amount &gt; 10,000** `Schedule R (demo)` rule with JSON `condition_logic`). If you already have a database from an older build, delete `backend/rules.db` (or point `DATABASE_URL` at a fresh file) and restart to load them.

Example request:

```bash
curl -s -X POST http://localhost:8000/api/validate-submission \
  -H "Content-Type: application/json" \
  -d '{
    "state": "CA",
    "tax_category": "sales_tax",
    "workflow_stage": "submission",
    "effective_date": "2026-04-28",
    "payload": {
      "documents": ["Form A"],
      "amount": 50000,
      "entity_type": "LLC",
      "submission_method": "portal"
    }
  }' | jq .
```

**Tests:** `cd backend && pytest`

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on **<http://localhost:8080>** and proxies `/api/*`
and `/health` to `http://localhost:8000` via `vite.config.ts`. Open
`/app/search` to ask a question, or use the sidebar to navigate.

### Run via Docker

```bash
docker compose up --build
```

Add `--profile postgres` and set
`DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/rules`
to use Postgres instead of SQLite.

## How to use it

### 1. Ask a state tax question

1. Open <http://localhost:8080/app/search>.
2. Pick a **State** and **Tax type** in the filter row (or leave them
   on `Any`).
3. Type a question (or click one of the example chips), hit
   **Search**.
4. Inspect the **Grounded answer** card, the rules-used list, and the
   **Why this answer?** sidebar with literal source snippets and links
   to the original documents/webpages.

### 2. Upload a PDF

1. Open <http://localhost:8080/app/sources>.
2. Drop a PDF in the **Drop PDFs to ingest** card (optionally tag it
   with state + tax type).
3. The backend extracts text (PyMuPDF → pdfplumber fallback), chunks
   it, and runs rule extraction. Auto-extracted rules show up in the
   review queue and on the search page.

### 3. Add a state tax website (URL)

1. Same page, **Add a state tax website** card.
2. Paste a URL (e.g. `https://www.cdtfa.ca.gov/taxes-and-fees/sutprograms.htm`).
3. Tag with state + tax type so retrieval can filter intelligently.

### 4. Run the curated source batch

The file `backend/app/data/sources.yaml` lists one **general_tax** portal
row per state (jurisdiction index) plus **pilot program** URLs for **CA /
NY / TX** (sales, payroll, withholding, franchise — see file header).
Run batch ingest to load what you need; full **50-state × portal** ingests
are long-running and may hit rate limits or HTTP errors on some sites.

- **From the UI:** Sources page → **Run ingestion** button.
- **From the API:** `curl -XPOST http://localhost:8000/api/ingest/run`.

You'll get a per-source breakdown (`ingested` / `duplicate` / `error`).
Already-ingested sources are skipped via SHA-256 checksum on the
extracted text — re-runs only pick up changes.

To add more states, append entries to `sources.yaml` and re-run.

### 5. Check for source updates (change monitoring)

Operators can re-validate indexed material without another full batch
ingest:

- **Dashboard:** **Check sources** — calls `POST /api/monitor/run` (same
  pipeline; default cap may differ from the Sources page).
- **Sources:** **Check for updates** — same run; see per-source
  `unchanged` / `updated` / `skipped` / `failed` in the last-run panel.

**API:** `POST /api/monitor/run` with an optional JSON body:

```json
{
  "source_ids": ["uuid-optional-subset"],
  "limit": 50,
  "auto_extract": true
}
```

Omitted `source_ids` walks sources ordered by oldest `updated_at` first,
capped by `limit` (default 50, max 200). **URL-backed** rows are fetched and
compared to the stored SHA-256 checksum; **unchanged** sources only get
`last_checked` bumped. **When content changes**, the pipeline
re-versions the source, replaces chunks, re-indexes vectors, and (if
`auto_extract` is true) **replaces extracted `Rule` rows for that
source** — treat published rules on that document as superseded by the
new extraction run. Upload-only / pasted / manual rows without a live
URL are **skipped** for fetch (status `skipped`) but still get
`last_checked` updated. Each run is recorded as an `IngestionRun` with
`kind: monitor` for analytics and the UI activity feed.

### 6. Admin review of low-confidence rules

Publishing is **governed** (engineer brief §8): a rule must be **Approved** before
**Publish**; publish also requires passing validation and **confidence ≥ 0.70**.
Program metadata (`program_variant`, effective date range, workflow stage)
is shown in the Review Queue and stored on each rule (brief §6).

1. Open <http://localhost:8080/app/review>.
2. Pick a rule from the queue. Inspect the original source snippet
   side-by-side with the extracted fields.
3. Use **Approve / Publish / Reject / Needs review**. Every action
   writes a `ReviewEvent` for full audit trail.

## How it maps to the PDF brief

| Brief capability                               | Implementation                                                              |
| ---------------------------------------------- | --------------------------------------------------------------------------- |
| 4.1 Rules Repository, canonical schema (§6)    | `Rule` ORM model + Pydantic schemas; review-status state machine            |
| 4.2 Forms / submission intelligence            | `required_forms`, `required_actions`, deadlines structured per rule         |
| 4.5 Continuous maintenance, ingestion          | `ingestion_service` + `seed_runner` + `POST /api/monitor/run` (checksum refresh) |
| 4.7 Cross-cutting: source ingestion + extraction | Hybrid LLM + deterministic heuristics; checksum-based dedupe              |
| §7 Functional: full traceability, citations    | Every Rule retains `source_id`, `source_url`, `source_snippet`              |
| §7 Optional human review console               | `/api/review/*` + Review Queue page                                         |
| §8 Explainability                              | `/api/query` always returns sources + confidence + method                   |
| §9.7 Modular monolith, AI/LLM abstraction      | One FastAPI app; OpenAI-compatible client; swappable provider               |
| §9.5 Confidence thresholds, exception routing  | `confidence_score` + `review_status ∈ {needs_review, auto_validated, …}`    |
| §9.5 Self-host fallback, no LLM dependency     | Deterministic answer + rule-extraction fallbacks if `LLM_API_KEY` is unset  |

## Smoke tests

From an empty DB (`DEMO_MODE=false`), after `uvicorn` is up:

```bash
# No sources yet — monitor returns zero items
curl -s -X POST http://localhost:8000/api/monitor/run \
  -H 'Content-Type: application/json' -d '{}' | jq .

# Ingest a manual row (no URL), then monitor — one item with status "skipped"
curl -s -X POST http://localhost:8000/api/ingest/source \
  -H 'Content-Type: application/json' \
  -d '{"source_type":"manual","title":"Test","state":"California","tax_type":"sales_tax","text":"Sample."}'
curl -s -X POST http://localhost:8000/api/monitor/run \
  -H 'Content-Type: application/json' -d '{}' | jq .
```

Frontend typecheck: `cd frontend && npx tsc --noEmit`

## Design notes

- **Why a modular monolith?** §9.7 of the brief recommends this for v1.
  Ingestion + extraction would be the most likely first
  service-extraction; the code is laid out so pulling them out later is
  mechanical.
- **Why no vector store yet?** Rule corpora at v1 are small; a careful
  lexical scorer with state/category prefilters returns sub-100ms top-k
  with zero infrastructure. The retrieval interface is intentionally
  narrow so a `pgvector` / Qdrant backend drops in cleanly.
- **Why a deterministic fallback?** Every demoable AI feature must
  degrade gracefully. With no `LLM_API_KEY`, ingestion still chunks +
  heuristically extracts rules, and Q&A still returns a structured
  answer assembled from retrieved rules with citations. The system
  never invents a tax rule.
- **Source traceability is non-negotiable.** Every extracted rule
  carries `source_id`, `source_document_name`, `source_url`, and a
  literal `source_snippet`. The `/api/query` response carries citations
  that point back into the same rows.

## Current limitations

- The retriever is lexical (BM25-ish + filters), not vector-based. Good
  for the v1 corpus size; would want pgvector at scale.
- Some state portals require JS / login walls — those would need
  Playwright (the brief mentions this as a v1.5 capability).
- The seed `sources.yaml` lists all **50 states** (portal index +
  **general_tax**) and pilot program pages for **CA / NY / TX**. Replace
  broken URLs as sites move; use **Run ingestion** / **monitor** for upkeep.
- No multi-tenant RBAC yet (the Admin page is cosmetic).

## Future roadmap

- pgvector embeddings + hybrid retrieval (BM25 + vector)
- Playwright-based ingestion for portals with JS / login walls
- Change detection: `POST /api/monitor/run` re-fetches URLs, compares
  checksums, and re-ingests when content changes (embedding distance and
  page-level diff are future work)
- Multi-tenant row-level security and SSO (OIDC/SAML)
- Outcome-feedback loop: link rejection codes back to the rule that
  applied at submission time (§4.4 of the brief)
- Workflow orchestration (Temporal) for multi-step verification →
  approval → submission flows
- Eval harness (golden-set per source) and canary publishing for new
  prompt/model versions

---

Seeded demo rules are clearly marked as illustrative. For production,
replace the seed sources with real authoritative URLs and PDFs ingested
via the Sources page or `/api/ingest/run`.
