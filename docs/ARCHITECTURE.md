# Architecture & Design

This document explains problem understanding, high-level design, database schema, external API integration, data flow, error handling and resilience, testing strategy, and trade-offs for the Groq AI Summarizer service.

## Problem understanding & assumptions

- Goal: provide a small REST microservice that accepts user text, uses an external LLM to produce a summary, persists the result, and exposes CRUD operations for summaries.
- Assumptions:
  - Inputs are unauthenticated JSON requests containing `input_text` as a string.
  - `input_text` length is between 20 and 10,000 characters (validated by Pydantic).
  - External LLM (Groq) may be slow or transiently fail; the service must be resilient (timeouts, retries).
  - Local development uses Docker Compose for Postgres; production would use a managed Postgres service.
  - No multi-tenant or per-user isolation is required for this exercise.

## High-level design and architecture

- Layered, concern-separated architecture:
  - API Layer: `app/main.py` — FastAPI endpoints, request/response wiring, dependency injection.
  - Validation Layer: `app/schemas.py` — Pydantic models for strict request/response validation.
  - Domain/Data Layer: `app/models.py`, `app/crud.py`, `app/db.py` — SQLAlchemy async models and DB session management.
  - Integration Layer: `app/groq_client.py` — encapsulates external LLM usage, with resilience.
  - Tests: `app/tests/` — unit/integration tests that mock external calls and DB access.

- Async-first implementation: FastAPI + SQLAlchemy async engine + AsyncPG for non-blocking I/O and good concurrency.

## Database schema and external API integration

- Table: `summaries`
  - `id` UUID PK
  - `input_text` (Text, not nullable)
  - `summary_text` (Text, not nullable)
  - `model` (Text, indicates source/model)
  - `created_at`, `updated_at` timestamps
  - Index on `created_at` to optimize time-ordered queries.

- External API (Groq LLM):
  - Encapsulated in `GroqClient` which wraps `AsyncGroq`.
  - Configuration-driven timeouts, retry count, and backoff are exposed via `app/config.py` (`GROQ_TIMEOUT`, `GROQ_RETRIES`, `GROQ_BACKOFF`).
  - Streaming response is concatenated into full text before storing.

## Data flow explanation (step-by-step)

1. Client POSTs JSON to `/summaries` with `input_text`.
2. FastAPI validates request body against `SummaryCreate` (Pydantic).
3. Endpoint calls `GroqClient.summarize(text)` which:
   - Executes the streamed completion call within an overall timeout.
   - Retries on transient failures with exponential backoff up to configured retries.
   - If successful, returns the full concatenated string; otherwise raises `ExternalServiceError`.
4. The API constructs a `Summary` ORM object and persists it to Postgres inside the async DB session.
5. The saved record is returned as the response (201 Created) using `SummaryOut` schema.

GET/PUT/DELETE endpoints use `crud.get_summary` for retrieval and operate against the same DB session.

## Error handling & resilience strategy

- Validation errors: FastAPI/Pydantic produce 422 responses; a custom exception handler formats and returns validation details.
- External LLM failures: `GroqClient` implements timeout + retries with exponential backoff. After retry exhaustion, `ExternalServiceError` (503) is raised.
- DB errors: SQLAlchemy errors are caught by a global exception handler that logs and returns a 500 response without leaking internals.
- Logging: critical failures are logged with stack traces to aid debugging. (Recommend adding structured logging for production.)

## Testing strategy (unit vs integration)

- Unit tests:
  - Test pure logic units (e.g., utility functions) without starting network/DB.
  - Mock the Groq client and verify that `create_summary` flow uses the returned string.

- Integration-style tests (fast, mocked):
  - Use AsyncClient from HTTPX to exercise FastAPI endpoints in-process.
  - Mock external LLM calls and DB CRUD functions to keep tests deterministic and fast.
  - Tests included: `app/tests/test_summaries.py` (POST flow) and `app/tests/test_endpoints.py` (GET/PUT/DELETE cases).

- Full integration (optional):
  - Run with test Postgres instance (e.g., Docker) and the real Groq endpoint in a staging environment; keep isolated and ephemeral DB volumes.

## Trade-offs, limitations, and improvements

- Trade-offs made:
  - Simplicity vs completeness: Authentication, rate-limiting, multi-tenancy were omitted to focus on core flow.
  - Mocked tests for speed vs full-system tests — we prefer fast iteration but recommend adding end-to-end tests.

- Limitations:
  - No rate-limiting or auth; a malicious client could flood requests and exhaust LLM quota.
  - No circuit-breaker; heavy LLM failures could cause resource pressure.

- Improvements (next steps):
  - Add authentication, rate-limiting, and request quotas per user.
  - Add a circuit-breaker/bulkhead around the Groq calls to fail fast when Groq is overloaded.
  - Add structured request tracing and metrics (Prometheus), and configure retries with jitter.
  - Add a containerized service for the app with Health and Readiness probes for orchestration.
  - Add more unit tests for edge cases and full integration tests with ephemeral DB.

## Closing notes

This implementation focuses on clear separation of concerns, async I/O, strict validation, and resilience when calling the external LLM. The README and tests are included to help reviewers evaluate behavior quickly. If you want, I can expand any of the sections above into deeper design docs or implement the suggested improvements.
