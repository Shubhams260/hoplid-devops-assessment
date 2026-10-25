# Hoplid Order Service — DevOps Assessment

A FastAPI order service backed by PostgreSQL, designed to demonstrate idempotent order creation, database-enforced duplicate protection, containerization, Kubernetes deployment, CI security checks, and operational testing.

## Architecture

- **API:** FastAPI with request validation and health endpoints.
- **Database:** PostgreSQL for durable order storage.
- **Idempotency:** `Idempotency-Key` header, request-payload hashing, and a unique database constraint on `(user_id, idempotency_key)`.
- **Containerization:** Docker and Docker Compose.
- **Orchestration:** Kubernetes Deployment and Service, health probes, resource requests and limits, rolling-update configuration, and Horizontal Pod Autoscaler.
- **Migrations:** Alembic migrations for legacy order-schema evolution.
- **CI:** GitHub Actions workflow for tests, image build, Trivy scans, and commit-SHA-tagged image publishing to GHCR.

## Prerequisites

- Docker Desktop with Docker Compose
- Git
- Python 3.12 recommended for local development
- `kubectl` for Kubernetes operations
- An accessible PostgreSQL instance for integration tests

## Run locally

Start the application and supporting services:

```bash
docker compose up --build -d
docker compose ps
```

Open the API documentation at `http://localhost:8000/docs`.

Health endpoints:

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

The readiness endpoint checks database connectivity.

## Create an order

Example using PowerShell:

```powershell
$body = '{"user_id":"user-101","vendor_id":"vendor-12","items":[{"item_id":"meal-7","quantity":2}]}'

Invoke-RestMethod `
  -Method Post `
  -Uri http://localhost:8000/api/orders `
  -Headers @{"Idempotency-Key"="demo-001"} `
  -ContentType "application/json" `
  -Body $body
```

Repeat the same request with the same key and payload. It should return the existing order rather than create another one. Reusing the key for the same user with a different payload should return HTTP 409.

## Run tests

Activate the project's Python virtual environment and install dependencies if required:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

**Verified locally:** 6 tests passed in 7.29 seconds.

Integration tests require the dedicated test database. Do not point destructive test fixtures at development, staging, or production databases.

## Kubernetes

The `k8s/` directory contains the API Deployment, Service, example database Secret manifest, and HPA configuration.

The local Kubernetes environment was verified with two API replicas. The deployment includes startup, readiness, and liveness probes, CPU and memory requests and limits, rolling-update settings, and a termination grace period.

Apply the manifests only after configuring a real database URL and the required Kubernetes Secret. Do not commit actual credentials.

The HPA is configured for 2–5 replicas with a 70% CPU utilization target. During the recorded load test, CPU utilization remained below the target and the deployment stayed at two replicas; scale-up was not demonstrated.

## Load-test results

Recorded on 2026-10-25 against the local Docker Desktop Kubernetes environment, using a Kubernetes Service port-forward and PostgreSQL.

| Metric | Observed result |
|---|---:|
| Requests | 200 |
| Client concurrency | 20 workers |
| Duration | 5.86 seconds |
| Throughput | 34.14 requests/second |
| Successful responses | 200 |
| Failed or non-2xx responses | 0 |
| Error rate | 0.00% |
| p50 latency | 517.64 ms |
| p95 latency | 937.02 ms |
| p99 latency | 1,046.15 ms |

These are results from one local test run, not production capacity guarantees. The run did not establish behavior under sustained overload or database failure.

See `docs/test-results.md` for recorded observations and limitations.

## Database migrations

The `migrations/` directory contains Alembic configuration and schema migrations intended to evolve the legacy orders schema.

Review the database URL in `alembic.ini` before running migrations. Validate migrations against a disposable database or a restored copy before applying them to any shared environment.

## CI/CD

`.github/workflows/ci.yml` implements the following GitHub Actions pipeline:

1. Runs the application tests against a PostgreSQL test database.
2. Builds the Docker image.
3. Runs Trivy filesystem and container image vulnerability scans, configured to fail on detected HIGH or CRITICAL findings, excluding unfixed vulnerabilities.
4. Publishes a Docker image to GitHub Container Registry (GHCR), tagged with the commit SHA, on pushes to `main`.

**Verified:** The GitHub Actions pipeline completed successfully on commit `969744f76a21aa9f8f2164e0ff4abecc094fbfc6`. All three jobs—application tests, container build and security scan, and immutable image publishing—passed.

The image was published to GHCR as `ghcr.io/shubhams260/hoplid-devops-assessment/hoplid-api`, tagged with the commit SHA. The package is currently private, so reviewers require appropriate access to pull it.

Automated Kubernetes deployment, rollout verification, and automatic rollback are not currently implemented in this workflow.

## Failure testing and recovery

Verified scenarios include:

- Repeated requests using the same idempotency key.
- Reusing a key with a different payload.
- Concurrent duplicate requests producing one database order.
- Replacing a terminated API pod and checking that the persisted order remained in PostgreSQL.

Not yet verified end-to-end:

- Database outage and connection-pressure behavior.
- A failed application release followed by a demonstrated rollback.
- A rolling deployment under continuous traffic.
- Automated latency/error-rate release gates.

See `docs/incident-postmortem.md` and `docs/test-results.md` for the recorded evidence and limitations.

## Security notes

- `.env`, virtual environments, Python caches, and test artifacts are excluded through `.gitignore`.
- `.env.example` and `k8s/db-secret.example.yaml` are templates only.
- Replace all local/example credentials before deploying to any shared environment.
- Do not commit real credentials or Kubernetes Secret values.
- The local Metrics Server configuration used for testing is not a production security recommendation.

## AI and tool disclosure

AI assistance was used during implementation and troubleshooting. The final submission should accurately describe the assistance received, the code and design decisions personally reviewed, and the commands and tests actually run. Do not claim unverified behavior or results.
