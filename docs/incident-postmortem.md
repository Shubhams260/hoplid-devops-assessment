# Recovery Test Report — Hoplid Order Service

## Purpose

This document records controlled recovery exercises for the local assessment environment. These are tests, not claims of production incidents.

## Scenario A: API pod replacement (previously tested)

### Impact
A single API pod was terminated during a controlled test.

### Detection
Kubernetes Deployment status and readiness were observed.

### Root cause
Intentional pod termination for resilience validation.

### Recovery
Kubernetes created a replacement pod. The Deployment returned to two running replicas, and the previously stored order remained in PostgreSQL.

### Preventive controls
- Multiple replicas and Kubernetes self-healing.
- Startup, readiness and liveness probes.
- Rolling-update settings and resource requests/limits.
- PostgreSQL-backed order persistence.
- Idempotency key and database uniqueness constraint.

### Limitations
This scenario did not demonstrate recovery from a PostgreSQL outage, a failed release, or a production incident.

## Scenario B: deliberately failed release (to be executed and evidenced)

Use `scripts/demo-failed-release.sh` only against the disposable local assessment cluster. The script changes the Deployment to a deliberately unavailable image, observes rollout failure, and restores the previously configured image in an exit trap.

Record the actual terminal output, timestamp, namespace, original image, injected image, rollout result, and final ready replicas here after running the test. Do not claim the scenario passed until the output confirms the original image was restored and the rollout became ready.

### Impact
The deliberately unavailable image prevented the replacement replica from becoming ready. The two original API pods remained Running and Ready during the failed rollout. No order request was sent as part of this failure-injection demonstration, so this test does not independently establish database integrity.

### Detection
`kubectl rollout status` timed out as expected. `kubectl get pods` showed the injected replacement in `ImagePullBackOff`, while the two original replicas remained ready.

### Root cause
Intentional use of an unavailable image tag.

### Recovery
The script's exit trap restored the original image `hoplid-api:local`. Kubernetes then reported `deployment "hoplid-api" successfully rolled out`, and the subsequent rollout-status check also succeeded. The immediate pod snapshot still showed the failed replacement Terminating. The final deployment and pod status are checked again during submission verification. This test restores only the application image; it does not reverse database migrations.

### Preventive actions
- Immutable image tags based on commit SHA.
- Automated unit, integration and migration tests before image publication.
- Dependency and image vulnerability scans.
- Deployment rollout/readiness and order smoke-test gate.
- Expand-and-contract schema changes.
- Application rollback kept separate from database migration rollback.

## WebSocket and in-flight work considerations

The current prototype does not implement a WebSocket endpoint. For a production extension, clients should reconnect with bounded exponential backoff and jitter, re-authenticate, and resubscribe to their order/status stream. Clients should reconcile order state from the durable API after reconnect rather than assuming every event was received.

During pod termination, the pre-stop drain hook should mark the pod unready, reject new application work, allow endpoint propagation, and let in-flight requests finish within the termination grace period. Requests that time out after a database commit must be retried with the same idempotency key.
