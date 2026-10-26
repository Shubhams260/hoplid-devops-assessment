# Architecture — Hoplid Order Service

## Overview

Hoplid is a FastAPI order service backed by PostgreSQL. It demonstrates idempotent order creation, database-enforced duplicate protection, containerization, Kubernetes orchestration, CI security scanning, and operational testing.

## High-Level Architecture

```text
Client
  |
  | POST /api/orders
  | Idempotency-Key
  v
FastAPI Application
  |
  | Request validation
  | Payload normalization and hashing
  | Idempotency lookup
  v
PostgreSQL
  |
  | Durable order records
  | Unique (user_id, idempotency_key) constraint
  v
Consistent order creation
```

## Request and Idempotency Flow

1. The client submits an order request with an `Idempotency-Key` header.
2. FastAPI validates the request and computes a hash of the normalized payload.
3. The service checks for an existing order associated with the same user and idempotency key.
4. If the key is reused with the same payload, the existing order is returned.
5. If the same key is reused for that user with a different payload, the service returns HTTP 409 Conflict.
6. PostgreSQL enforces uniqueness on `(user_id, idempotency_key)`, protecting against concurrent duplicate requests.

An initial database lookup alone cannot prevent races: concurrent requests may both observe that no matching order exists. The database uniqueness constraint is the final concurrency guard.

## Runtime and Deployment

- **Application:** FastAPI served by Uvicorn.
- **Database:** PostgreSQL.
- **Local development:** Docker Compose.
- **Container image:** Built through GitHub Actions and published to GitHub Container Registry using a commit-SHA tag.
- **Kubernetes:** Deployment and Service with startup, readiness, and liveness probes, resource requests and limits, rolling-update settings, and a Horizontal Pod Autoscaler.
- **Database migrations:** Alembic migrations for legacy order-schema evolution.

## Health and Operational Checks

The service exposes:

- `GET /health` — general health check.
- `GET /health/live` — liveness check.
- `GET /health/ready` — readiness check, including database connectivity.

Local Kubernetes testing verified two API replicas, duplicate-request handling, pod replacement, and a 200-request load test. The recorded load test achieved 34.14 requests per second with zero failed requests in that run.

## CI/CD Pipeline

The GitHub Actions workflow runs PostgreSQL-backed application tests, builds the container, scans the filesystem and image using Trivy, and publishes the image to GHCR when changes are pushed to `main`.

The pipeline has completed successfully. Automated Kubernetes deployment and automatic rollback are not implemented in the current workflow.

## Limitations

The project has not demonstrated database-outage recovery, sustained overload behavior, a rolling deployment under continuous traffic, or an automated release rollback. The recorded load-test results are from a local development environment and should not be treated as production capacity guarantees.

See `../README.md` and `test-results.md` for setup instructions, test evidence, and measured results.

## Horizontal Scaling Policy

The API uses a Kubernetes Horizontal Pod Autoscaler (HPA) targeting average CPU utilization.

- **Metric:** CPU utilization relative to each pod's CPU request.
- **Target:** 70% average CPU utilization.
- **Minimum replicas:** 2.
- **Maximum replicas:** 5.
- **Scale-up behavior:** No stabilization delay; policies permit up to two additional pods or a 100% increase per 60-second policy period, subject to Kubernetes HPA calculations and the replica limit.
- **Scale-down behavior:** Five-minute stabilization window, with a maximum 50% reduction per 60-second policy period.
- **Resource requests:** 100m CPU and 128Mi memory per API container.
- **Resource limits:** 500m CPU and 256Mi memory per API container.

The policy assumes CPU utilization is a useful indicator of API demand. CPU-based scaling may not respond adequately to database connection exhaustion, slow database queries, network waits, or other I/O-bound bottlenecks. Those conditions require separate monitoring and operational response.

The local cluster currently reports valid CPU metrics. The observed workload has been low (approximately 2–3% CPU utilization), so actual HPA scale-up has not yet been demonstrated. Earlier HPA events reported missing metrics during a transient period. The configured policy is not evidence by itself that scale-up has been validated.

The local test environment does not establish production capacity or availability guarantees. Production tuning should use representative sustained load, database capacity measurements, and observed latency/error objectives.
