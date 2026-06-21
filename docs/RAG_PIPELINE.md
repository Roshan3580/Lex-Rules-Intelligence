# RAG Pipeline

## Goal

Provide **source-backed retrieval** over tax and compliance sources so answers cite evidence—not free-form model knowledge.

Lex implements a RAG-style pipeline with structured rule records, confidence scoring, and human review—not a thin chat wrapper.

## Pipeline stages

### 1. Source ingestion

**Inputs:**

- PDF uploads (`POST /api/sources/upload`)
- Regulator URLs (`POST /api/sources/url`)
- Pasted text (`POST /api/sources/text`)
- Single structured ingest (`POST /api/ingest/source`)
- Curated batch list in `backend/app/data/sources.yaml` (`POST /api/ingest/run`)

Each source stores type, URL/path, state, tax category, checksum, and processing status.

### 2. Text extraction

- **HTML** — `requests` + BeautifulSoup
- **PDF** — PyMuPDF with pdfplumber fallback
- **Plain text** — stored directly from uploads or paste

Failed extractions mark the source as `failed` with an error message.

### 3. Chunking

`backend/app/utils/chunking.py` splits extracted text into sentence-aware segments. Chunks are persisted as `SourceChunk` rows linked to their parent `Source`.

### 4. Rule extraction

`extraction_service.py` runs hybrid extraction:

- **LLM path** — when `LLM_API_KEY` is set, structured fields are parsed from model output
- **Heuristic path** — deterministic patterns when no LLM is available

Outputs include rule title, summary, required forms/actions/deadlines, `confidence_score`, and suggested `review_status` (`auto_validated`, `needs_review`, etc.).

### 5. Indexing

- **Relational store** — rules and chunks in SQLite/PostgreSQL
- **Vector index** — optional NumPy in-process index (`VECTOR_BACKEND=numpy`) fed by hash or OpenAI-compatible embeddings (`EMBEDDING_PROVIDER`)

Reindex endpoint: `POST /api/sources/reindex`

### 6. Query handling

`POST /api/query` accepts:

```json
{
  "question": "What are the sales tax filing requirements in California?",
  "state": "California",
  "tax_type": "sales_tax"
}
```

Questions are persisted; answers are stored with retrieval metadata.

### 7. Retrieval

`retrieval_service.py` supports three modes:

| Mode | Behavior |
| --- | --- |
| `lexical` | Token overlap scoring (default at small corpus sizes) |
| `vector` | Cosine similarity over embedding index |
| `hybrid` | Weighted fusion of lexical + vector + confidence + freshness + published boost |

Filters apply **before** ranking: state, tax category, workflow stage, review status.

### 8. Answer generation

`answer_service.py`:

1. Retrieves top rules and chunks
2. Checks evidence sufficiency
3. Generates via LLM (if configured) or **deterministic fallback** summary
4. Runs safety checks on fabricated specifics
5. Persists `Answer` with `method`, `confidence`, chunks used, and source versions

### 9. Citations and confidence

Responses include:

- `rules_used` — full structured rule objects
- `sources` — title, URL, snippet, document type, `last_checked`, relevance
- `confidence` — numeric score reflecting retrieval strength and validation signals
- `method` — `llm` or `fallback`

The UI surfaces citations, confidence bars, and source snippets in Rule Search.

### 10. Human review

Rules with low confidence or validation signals land in `draft`, `needs_review`, or `auto_validated` states. Reviewers approve or reject before **publish**. Published rules receive retrieval boost but still retain source linkage.

## Why not just a chatbot?

| Chatbot wrapper | Lex |
| --- | --- |
| Answers from model weights | Answers from retrieved sources |
| Opaque provenance | Citations + snippets + URLs |
| Uniform confidence | Per-answer and per-rule scores |
| No operational records | Structured `Rule` entities |
| Hard to audit | `ReviewEvent` + ingestion history |

## Limitations

- **Source coverage** — quality depends on what has been ingested; empty DB → empty answers.
- **Extraction errors** — heuristics and LLMs can misparse complex regulatory text.
- **Human review required** — for high-stakes tax/compliance decisions.
- **Not legal or tax advice** — portfolio prototype with illustrative demo data.
- **Ingestion constraints** — JavaScript-heavy or login-walled sites may fail without a browser automation layer (not included here).
