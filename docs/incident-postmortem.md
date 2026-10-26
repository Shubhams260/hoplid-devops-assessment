# Recovery Test Report — Hoplid Order Service

These are controlled local assessment tests, not production incidents.

## Scenario A: API pod replacement

A pod was intentionally terminated. Kubernetes replaced it, the Deployment returned to two ready replicas, and the previously stored order remained in PostgreSQL.

This local test does not establish production availability guarantees.

## Scenario B: deliberately failed release — completed

**Environment:** Docker Desktop Kubernetes, namespace `default`, Deployment `hoplid-api`.

**Original image:** `hoplid-api:local`

**Injected image:** `hoplid-api:deliberately-missing-for-recovery-demo`

### Impact and detection

The injected image prevented the replacement pod from starting. The rollout timed out as expected, and the replacement entered `ImagePullBackOff`. The two existing API replicas remained ready.

### Root cause

Intentional use of an unavailable image tag to simulate a failed release.

### Recovery

The script's exit trap restored `hoplid-api:local`. Kubernetes reported a successful rollout after restoration. Final verification showed 2/2 replicas ready, updated and available; both API pods were Running with zero restarts.

This was scripted local image restoration, not an automatic rollback triggered by GitHub Actions. No order request was sent during this failure injection, so database integrity was not independently tested by this scenario.

### Preventive actions

- Immutable commit-SHA image tags.
- Automated tests and vulnerability scans before image publication.
- Deployment readiness and order-creation verification.
- Expand-and-contract database changes.
- Application rollback kept separate from database migration rollback.

## WebSocket and in-flight work

The prototype does not implement a WebSocket endpoint. A production extension should reconnect clients with bounded exponential backoff and jitter, re-authenticate, resubscribe, and reconcile order state through the durable API.

During termination, the pre-stop hook asks the application to drain, fail readiness and reject new application requests. Completion of concurrent in-flight requests and exact endpoint-propagation timing have not been fully demonstrated. Uncertain order submissions should be retried using the same idempotency key.
