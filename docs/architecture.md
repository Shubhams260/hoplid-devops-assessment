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
