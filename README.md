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

Recorded on 2026-10-25 and 2026-10-26 against local Docker Desktop Kubernetes, using a Kubernetes Service port-forward and PostgreSQL.

### Run 1 — 2026-10-25

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

### Run 2 — 2026-10-26

| Metric | Observed result |
|---|---:|
| Requests | 200 |
| Client concurrency | 20 workers |
| Duration | 7.93 seconds |
| Throughput | 25.22 requests/second |
| Successful responses | 200 |
| Failed requests | 0 |
| Error rate | 0.00% |
| p50 latency | 598.57 ms |
| p95 latency | 2,590.64 ms |
| p99 latency | 2,691.80 ms |

Reproduce Run 2 while the Kubernetes API Service is port-forwarded to local port 8000:

```bash
./.venv/bin/python loadtest/load_test.py \
  --base-url http://127.0.0.1:8000 \
  --requests 200 \
  --concurrency 20
```

Both runs completed with zero failed requests. In Run 2, both API pods remained ready with zero restarts, CPU was approximately 2 millicores per pod, memory was 60–63 MiB, and HPA CPU utilization was 2% against a 70% target. The deployment remained at two replicas; scale-up was not demonstrated.

These are local test observations, not production capacity guarantees. Run 2 had higher p95 and p99 latency, warranting further investigation. These runs were not a controlled performance comparison and do not establish behavior under sustained overload, database failure, or rolling deployment under traffic.

See `docs/test-results.md` for full observations and limitations.

## Database migrations

The `migrations/` directory contains Alembic configuration and schema migrations intended to evolve the legacy orders schema.

Review the database URL in `alembic.ini` before running migrations. Validate migrations against a disposable database or a restored copy before applying them to any shared environment.

## CI/CD

`.github/workflows/ci.yml` runs unit tests, integration tests, a dedicated migration test, container build and Trivy scans. On pushes to `main`, it publishes a GHCR image tagged with the full commit SHA.

**Verified:** [GitHub Actions run #21](https://github.com/Shubhams260/hoplid-devops-assessment/actions/runs/40281210587) passed all four jobs for commit `e12c400`. Check the Actions page for the newest run after this update.

This workflow publishes an image; it does not automatically deploy to the local Kubernetes cluster or automatically trigger a rollback. GHCR package visibility is separate from repository visibility.

## Failure testing and recovery

Verified scenarios include:
- Idempotent retries and HTTP 409 for a reused key with a different payload.
- Concurrent duplicate requests producing one durable order.
- Isolated database failure and connection-pool pressure tests, with documented limitations.
- Pod termination during a load-test run and Kubernetes replacement.
- A deliberately failed local rollout: the unavailable image entered `ImagePullBackOff`, rollout timed out, and the script restored `hoplid-api:local`. Final verification showed 2/2 replicas ready.

The failed-release demonstration validates local failure detection and scripted image restoration. It does not demonstrate an automatic rollback triggered by GitHub Actions or independently prove database integrity during that particular test.

Not fully verified:
- API-wide pool exhaustion under sustained overload.
- Automated latency/error-rate release gates.
- The final status-code read-path cutover and removal of the legacy text column.
- Runtime WebSocket reconnection; the prototype does not implement a WebSocket endpoint.
- Production-scale migration performance or zero-downtime guarantees.

See `docs/incident-postmortem.md` and `docs/test-results.md` for actual observations and limitations.

## Security notes

- `.env`, virtual environments, Python caches and test artifacts are excluded by `.gitignore`.
- `.env.example` and `k8s/db-secret.example.yaml` are templates for local development only.
- `k8s/api.yaml` contains the Deployment and Service, not a hardcoded drain-token Secret. Provision `hoplid-db` and `hoplid-drain` separately.
- Compose uses `hoplid_local_only` as a local development password. Never reuse it in a shared environment.
- Gitleaks reported no findings across 22 commits or the current files when scanned. Automated scanning cannot guarantee detection of every sensitive value.
- The local Metrics Server configuration used during testing is not a production security recommendation.

## AI and tool disclosure

AI assistance was used to draft and refine code, the workflow, migration strategy, shell scripts, documentation and troubleshooting. Commands and tests were run during development, and design decisions should be explained by the author during review.

Observed evidence includes a successful GitHub Actions run, an isolated PostgreSQL migration test, Gitleaks scans, unit tests, and a local Kubernetes failed-release/restoration test. Limitations documented in this repository remain; unverified behavior is not presented as a production guarantee.
