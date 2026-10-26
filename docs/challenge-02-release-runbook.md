# Challenge 02 release runbook

## CI behavior

Pull requests and pushes to `main` run unit tests, integration tests, a migration test against a separately seeded disposable PostgreSQL service, a container build, and HIGH/CRITICAL Trivy scans. On a push to `main`, the workflow publishes `ghcr.io/<owner>/hoplid-api:<full-commit-sha>` using `GITHUB_TOKEN`; no registry password is stored in source.

The publish job uploads an immutable image; it does not automatically deploy to the local WSL/Docker Desktop cluster. A GitHub-hosted runner cannot access a local cluster without a deliberately configured self-hosted runner or another secure deployment mechanism. Local deployment is verified with the script below.

## Local pre-release verification

```bash
NAMESPACE=default BASE_URL=http://localhost:8000 ./scripts/verify-deployment.sh
```

The script checks rollout status, replica readiness, health endpoints, a new order, a retry returning the same order ID, and HTTP 409 for the same key with a changed payload. It creates one uniquely keyed test order.

## Failed-release demonstration

Only on the local assessment cluster:

```bash
ALLOW_FAILURE_DEMO=yes ./scripts/demo-failed-release.sh
```

The script temporarily sets a deliberately unavailable image, waits for rollout failure, captures deployment/pod diagnostics, and restores the original image using an exit trap. Run only on the local assessment cluster, not production. Verify the final rollout manually after the script. Do not claim the demonstration succeeded until recovery output is captured.

## Application rollback

```bash
NAMESPACE=default ./scripts/rollback-release.sh
```

This reverts the Kubernetes Deployment to the previous revision and waits for rollout. It does not downgrade Alembic.

## Database rule

Prefer additive, roll-forward-compatible schema changes. A failed application rollout does not imply that the database migration should be reversed. Keep expanded schema until old and new versions no longer need compatibility; contract in a later release.
