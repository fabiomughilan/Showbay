# Groq AI Summarizer Service - Fabio Mughilan


Overview
-- An async FastAPI service that sends user text to Groq's Llama 3 model and stores generated summaries in PostgreSQL.

Prerequisites
- Docker & Docker Compose (for Postgres)
# Groq AI Summarizer Service

This repository implements a small, production-oriented FastAPI microservice that accepts
long text, sends it to an external LLM (Groq Llama 3), and persists the generated summary
in PostgreSQL.

## Problem Understanding & Assumptions

- Interpretation: implement a microservice that exposes CRUD endpoints for "summaries" and
  uses an external LLM for automatic summarization on create.
- Use Case: "AI-Powered Text Summarizer" — users post long text and receive concise summaries that are stored for retrieval and editing.
- Assumptions:
  - Requests will send JSON with an `input_text` string between 20 and 10,000 characters.
  - No user authentication is required for this exercise (requests are unauthenticated).
  - External LLM (Groq) can fail or be slow; service should retry and fail fast when necessary.
  - The project runs locally in development with Docker for Postgres.

## Design Decisions

- Database Schema:
  - Single table `summaries` with UUID primary key, `input_text`, `summary_text`, `model`, `created_at`, `updated_at`.
  - Index on `created_at` (`ix_summaries_created_at`) to support time-ordered queries.

- Project Structure (layered by concern):
  - `app/main.py` — API entry, dependency wiring, global handlers
  - `app/config.py` — settings loaded from `.env`
  - `app/db.py` — async SQLAlchemy engine and session factory
  - `app/models.py` — SQLAlchemy ORM models
  - `app/schemas.py` — Pydantic request/response models
  - `app/crud.py` — DB helper functions
  - `app/groq_client.py` — external API integration, with timeouts/retries
  - `app/tests/` — pytest test-suite

- Validation Logic:
  - Pydantic is used for request/response validation.
  - `SummaryCreate.input_text` enforces `min_length=20` and `max_length=10000`.
  - Additional integrity (e.g., content-type checks) are enforced by FastAPI and tests.

- External API Design:
  - The Groq client wraps `AsyncGroq` with an overall timeout and retry/backoff strategy configurable via `.env` (`GROQ_TIMEOUT`, `GROQ_RETRIES`, `GROQ_BACKOFF`).
  - On repeated failures, the service raises an `ExternalServiceError` (HTTP 503).

## Solution Approach (data flow)

1. Client POSTs to `/summaries` with `{"input_text": "..."}`.
2. FastAPI validates payload using `SummaryCreate`.
3. `app.groq_client.GroqClient.summarize` calls the external LLM with timeout+retries and streams the response.
4. Server creates a `Summary` ORM instance, persists it in Postgres, and returns the stored record (201 Created).
5. Clients may `GET`, `PUT`, or `DELETE` the resource using the UUID.

## Error Handling Strategy

- External failures: `GroqClient` performs retries with exponential backoff; if exhausted, raises `ExternalServiceError` which is mapped to HTTP 503 by a global exception handler in `app/main.py`.
- Database errors: a global handler maps SQLAlchemy exceptions to a 500 response and logs the traceback.
- Request validation: `RequestValidationError` returns a 422 with validation details.

Global exception handlers are registered in `app/main.py` and log useful diagnostics while returning proper HTTP codes.

## How to Run

1. Copy and edit env (example provided):

```bash
cp .env.example .env
# Edit .env and set GROQ_API_KEY and DATABASE_URL if needed
```

Example `.env.example` values (already included in repo):
```
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/summaries
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT=30
GROQ_RETRIES=3
GROQ_BACKOFF=1.0
```

2. Start Postgres (docker):

```bash
docker compose up -d
```

3. Install dependencies and run the app:

```bash
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

4. API docs are available at `http://127.0.0.1:8000/docs`.

## Testing

- Run tests (the suite mocks the external LLM):

```bash
pytest
```

The tests cover the `POST /summaries` flow and additional CRUD endpoint behavior via mocked DB and Groq client.

## Troubleshooting

- Database credential issues:
  - If you change the `POSTGRES_PASSWORD` after the DB container was first created, the persisted Docker volume retains the old DB, so the password won't update. Recreate the container and volume with `docker compose down -v` then `docker compose up -d` to reset.
- Port conflicts:
  - If `5432` is already used by a local DB, either stop the local service or remap Docker (e.g., `5433:5432`) and update `DATABASE_URL`.
- Encoding in `DATABASE_URL`:
  - Percent-encode special characters in passwords (e.g., `@` -> `%40`).

## Design Notes & Next Steps

- Observability: add request/response logging and structured logs for production.
- Resilience: consider circuit-breaker or bulkhead patterns for the external LLM to avoid resource exhaustion.
- Scaling: add pagination, rate-limiting, and authentication as next steps for production use.

---

If you want, I can now:

- add request logging and structured logs;
- add health-check test(s) and expand unit test coverage; or
- add Dockerfile for the app and containerized dev workflow.
