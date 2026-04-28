# State Tax Rules Intelligence Platform

A production-style prototype that turns fragmented state tax law sources
(PDFs, government portals, bulletins, uploaded documents, pasted text)
into structured, searchable, source-backed workflow intelligence.

It is **not** a chatbot wrapper — every answer is grounded in indexed
sources, returns citations and a confidence score, and routes
low-confidence rules to a human review console. The data model and
ingestion pipeline are inspired directly by the canonical rule schema in
the engineering brief (Sections 4–9 of `Product Overview - Derrick Lewis -
Stealth Startup - v2.pdf`).

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

1. Filters by state and tax category (if provided).
2. Retrieves relevant rules and source chunks.
3. Generates a grounded answer (LLM if configured, otherwise a
   deterministic fallback that summarizes the top-ranked rules).
4. Returns **citations**, a **confidence score**, and the **rules
   used** so the user can verify everything against the original source.

It also lets operators **upload PDFs, ingest URLs, or paste text**;
auto-extracts candidate rules; and routes anything below a confidence
threshold to an **admin review queue** for edit / approve / publish /
reject actions, with a full audit trail.

## How it maps to the PDF brief

| Brief capability                                 | Implementation                                                             |
| ------------------------------------------------ | -------------------------------------------------------------------------- |
| 4.1 Rules Repository, canonical schema (§6)      | `Rule` ORM model + Pydantic schemas; review-status state machine           |
| 4.2 Forms / submission intelligence              | `required_forms`, `required_actions`, `submission_method`-style metadata    |
| 4.5 Continuous maintenance, ingestion            | `ingestion_service` (PDF/URL/text/upload), chunked storage, source lineage |
| 4.7 Cross-cutting: source ingestion + extraction | `extraction_service` with hybrid LLM + deterministic heuristics            |
| §7 Functional: full traceability, citations      | Every `Rule` retains `source_id`, `source_url`, `source_snippet`           |
| §7 Optional human review console                 | `/api/review` endpoints + Admin Review page                                |
| §8 Explainability                                | Answer payload always returns citations + confidence + method              |
| §9.7 Modular monolith, AI/LLM abstraction        | Single FastAPI app with clean service boundaries; OpenAI-compatible client |
| §9.5 Confidence thresholds, exception routing    | `confidence_score` + `review_status` ∈ {needs_review, auto_validated, ...} |
| §9.5 Self-host fallback, no LLM dependency       | Deterministic answer + rule-extraction fallbacks if `LLM_API_KEY` is unset |

## Architecture

This is a **modular monolith** (per §9.7 of the brief — extract to
services later, only when load or team boundaries justify it).

```
┌─────────────────────────────┐         ┌──────────────────────────────────────┐
│   React + TS + Tailwind     │  /api   │  FastAPI                             │
│   (Vite, shadcn/ui)         │ ──────▶ │  ┌─────────────────────────────────┐ │
│   pages: Ask, Rules,        │         │  │ routers/ (sources, rules,       │ │
│   Sources, Admin Review     │         │  │           questions, review)    │ │
└─────────────────────────────┘         │  └────────────────┬────────────────┘ │
                                        │                   │                  │
                                        │  ┌────────────────▼────────────────┐ │
                                        │  │ services/                       │ │
                                        │  │  ingestion → extraction →       │ │
                                        │  │  retrieval → answer → review    │ │
                                        │  └────────────────┬────────────────┘ │
                                        │                   │                  │
                                        │  ┌────────────────▼────────────────┐ │
                                        │  │ SQLAlchemy models               │ │
                                        │  │ Source · SourceChunk · Rule     │ │
                                        │  │ Question · Answer · ReviewEvent │ │
                                        │  └────────────────┬────────────────┘ │
                                        └────────────────────┼─────────────────┘
                                                             │
                                                  ┌──────────▼─────────┐
                                                  │ SQLite (default)   │
                                                  │ or PostgreSQL      │
                                                  └────────────────────┘
```

```
backend/
  app/
    main.py                  # FastAPI app + startup (init DB, seed demo data)
    config.py                # Settings (env-driven, OpenAI-compatible LLM)
    database.py              # SQLAlchemy engine + session
    models.py                # Sources, chunks, rules, Q&A, review events
    schemas.py               # Pydantic DTOs
    seed.py                  # CA / TX / NY demo data
    routers/
      sources.py             # Upload PDF, ingest URL, ingest text, list/delete
      rules.py               # List / get / create rules
      questions.py           # POST /api/ask
      review.py              # Admin queue + edit/approve/reject/publish
    services/
      ingestion_service.py   # PDF + URL + text + uploads → chunks
      extraction_service.py  # Hybrid LLM + heuristic rule extraction
      retrieval_service.py   # Lexical retrieval over rules + chunks
      answer_service.py      # RAG flow: retrieve → answer → cite
      review_service.py      # Edit/approve/reject/publish + audit trail
    utils/
      chunking.py            # Sentence-aware text chunker
      llm_client.py          # OpenAI-compatible HTTP client + JSON parser
  requirements.txt
  .env.example
  Dockerfile

frontend/
  src/                       # Vite + React + TS + Tailwind + shadcn/ui
  package.json
  vite.config.ts
  Dockerfile

docker-compose.yml           # backend + frontend (+ optional Postgres profile)
```

## Setup instructions

### Prerequisites

- Python 3.11+
- Node 20+
- (Optional) Docker

### Environment variables

`backend/.env.example` shows the full set. The most important ones:

| Var             | Default                              | Notes                                 |
| --------------- | ------------------------------------ | ------------------------------------- |
| `DATABASE_URL`  | `sqlite:///./rules.db`               | Set Postgres URL to switch DBs        |
| `LLM_API_KEY`   | *(empty)*                            | If empty, uses deterministic fallback |
| `LLM_BASE_URL`  | `https://api.openai.com/v1`          | Any OpenAI-compatible endpoint        |
| `LLM_MODEL`     | `gpt-4o-mini`                        | Model name for extraction + answers   |
| `FRONTEND_ORIGIN` | `http://localhost:5173`            | CORS allowlist for the dev server     |
| `UPLOAD_DIR`    | `./uploads`                          | Where uploaded files are written      |

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

On first start the app creates SQLite tables and seeds demo rules for
California, Texas, and New York. The OpenAPI docs are at
<http://localhost:8000/docs>.

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The dev server runs on <http://localhost:5173> and proxies `/api/*` to
`http://localhost:8000` via `vite.config.ts`.

### Run via Docker

```bash
docker compose up --build
```

Add `--profile postgres` and set `DATABASE_URL=postgresql+psycopg2://postgres:postgres@postgres:5432/rules`
to use Postgres instead of SQLite.

## How to use it

### Ask a state tax question

1. Open the **Ask** page.
2. (Optional) Pick a state and tax category.
3. Type a question or click one of the example chips.
4. Inspect the answer panel, the **Source citations** sidebar, the
   **Rules used** list, and the confidence badge.

### Upload a PDF

1. Open the **Sources** page.
2. Use the **Upload a document** card. Choose a state and tax category
   so retrieval can filter intelligently.
3. The backend extracts text (PyMuPDF → pdfplumber fallback), chunks
   it, and runs rule extraction (LLM if configured; heuristic
   otherwise). Auto-extracted rules show up in the Rules and Admin
   Review pages.

### Ingest a URL

1. Open the **Sources** page → **Ingest a URL**.
2. Paste a state-government URL (e.g. a CDTFA bulletin page). The
   crawler fetches, strips nav/footer/script, chunks, and extracts.

### Admin review of low-confidence rules

1. Open the **Admin Review** page.
2. Pick a rule from the queue. Edit any field; one-click **Approve**,
   **Publish**, **Reject**, or send back to **Needs review**.
3. Every change writes a `ReviewEvent` for full audit trail.

## API surface (high-level)

| Method | Path                                | Purpose                              |
| ------ | ----------------------------------- | ------------------------------------ |
| GET    | `/api/health`                       | Status + LLM mode + DB type          |
| POST   | `/api/sources/upload`               | Multipart upload (PDF/TXT/HTML)      |
| POST   | `/api/sources/url`                  | Ingest a URL                         |
| POST   | `/api/sources/text`                 | Ingest pasted text                   |
| GET    | `/api/sources`                      | List sources                         |
| DELETE | `/api/sources/{id}`                 | Delete a source                      |
| GET    | `/api/rules`                        | List rules (filter by state/cat/status) |
| POST   | `/api/rules`                        | Create a rule manually               |
| POST   | `/api/ask`                          | RAG Q&A with citations               |
| GET    | `/api/review/queue`                 | Rules needing human review           |
| PATCH  | `/api/review/rules/{id}`            | Edit a rule                         |
| POST   | `/api/review/rules/{id}/action`     | approve / reject / publish / needs_review |
| GET    | `/api/review/rules/{id}/events`     | Audit trail                          |

## Design notes

- **Why a modular monolith?** The brief's §9.7 explicitly recommends
  this for v1. Ingestion + extraction would be the most likely first
  service-extraction; the code is laid out so that pulling them out
  later is mechanical.
- **Why no vector store yet?** Rule corpora at v1 are small; a careful
  lexical scorer with state/category prefilters returns sub-100ms top-k
  with zero infrastructure. The `retrieval_service` interface is
  intentionally narrow so a `pgvector`/Qdrant backend drops in cleanly.
- **Why a deterministic fallback?** Every demoable AI feature must
  degrade gracefully. With no `LLM_API_KEY`, ingestion still chunks +
  heuristically extracts rules, and Q&A still returns a structured
  answer assembled from retrieved rules with citations.
- **Source traceability is non-negotiable.** Every extracted rule
  carries `source_id`, `source_document_name`, `source_url`, and a
  literal `source_snippet`. The Q&A response carries citations that
  point back into the same rows.

## Future roadmap

- pgvector embeddings + hybrid retrieval (BM25 + vector)
- Headless-browser ingestion (Playwright) for portals with JS / login walls
- Change detection: page-level hashing + embedding distance, with
  impact analysis on rules referencing changed passages
- Multi-tenant row-level security and SSO (OIDC/SAML)
- Outcome-feedback loop: link rejection codes back to the rule that
  applied at submission time (§4.4 of the brief)
- Workflow orchestration (Temporal) for multi-step verification →
  approval → submission flows
- Eval harness (golden-set per source) and canary publishing for new
  prompt/model versions

---

The seeded demo rules are clearly marked as illustrative. For
production, replace the seed sources with real authoritative URLs and
PDFs ingested via the Sources page.
