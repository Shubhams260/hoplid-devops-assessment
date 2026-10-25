# Architecture (current prototype)

Client -> FastAPI -> PostgreSQL

The client submits `POST /api/orders` with an `Idempotency-Key`. FastAPI validates and hashes the normalized payload. PostgreSQL is the durable source of truth. A database uniqueness constraint on `(user_id, idempotency_key)` protects against concurrent duplicate requests.

Docker Compose runs the API and PostgreSQL locally. Kubernetes, CI/CD, observability, load testing, and migration compatibility are not implemented yet and must not be described as implemented until verified.

An initial SELECT alone is not sufficient: concurrent requests can both observe no row. The unique database constraint is the final concurrency guard.
