# Recovery Test Report — Hoplid Order Service

## Purpose

This report documents a controlled Kubernetes pod-replacement test. It is a recovery test, not a report of a production incident.

## Scenario

An API pod running in the local Docker Desktop Kubernetes environment was deliberately terminated to verify that the Kubernetes Deployment would replace it and that an existing order would remain persisted in PostgreSQL.

## Expected Behavior

- Kubernetes should create a replacement API pod and restore the desired replica count.
- The application should become ready after the replacement starts.
- An order previously stored in PostgreSQL should remain available because its persistence is independent of the API pod lifecycle.

## Observed Result

The terminated API pod was replaced, the Deployment returned to two running replicas, and the previously created order remained persisted in PostgreSQL.

## Data Integrity Verification

The existing order was checked after pod replacement. The order remained in the database.

## Preventive and Resilience Mechanisms

The deployment configuration includes:

- Kubernetes Deployment replica management.
- Startup, readiness, and liveness probes.
- Rolling-update configuration.
- Resource requests and limits.
- PostgreSQL-backed order persistence.

These mechanisms support application recovery and operational resilience, but do not guarantee recovery from every failure scenario.

## Limitations

This test does not demonstrate recovery from a PostgreSQL outage, a failed application release, a rolling deployment under continuous traffic, or an automated rollback. No production incident is claimed.

## Evidence

The test was performed against the local Docker Desktop Kubernetes environment. The associated deployment and test observations are documented in the project README and `test-results.md`.

For reproducible verification, use the deployment verification script at `scripts/verify-deployment.sh` with the local Kubernetes environment running and the API accessible at the configured base URL.
