# Test and load-test results

## Kubernetes API Load Test — 2026-10-25

### Environment
- Deployment: `hoplid-api` on local Docker Desktop Kubernetes
- Database: PostgreSQL
- Access path: Kubernetes Service through local port-forward
- Requests: 200 unique order creation requests
- Client concurrency: 20 worker threads

### Results
| Metric | Observed result |
|---|---:|
| Total duration | 5.86 seconds |
| Throughput | 34.14 requests/second |
| Successful HTTP responses (2xx) | 200 |
| Non-2xx or failed requests | 0 |
| Error rate | 0.00% |
| p50 latency | 517.64 ms |
| p95 latency | 937.02 ms |
| p99 latency | 1046.15 ms |

### Kubernetes observations
- HPA CPU target: 2% / 70%
- Minimum and maximum replicas: 2 and 5
- Replicas observed after the test: 2
- Pod CPU: approximately 2–3 millicores
- Pod memory: approximately 59–60 MiB
- Pod restarts: 0

### Interpretation and limitations
All 200 requests succeeded in this run. The workload did not trigger scale-up because measured CPU utilization remained well below the HPA target. These are local-environment results, not production capacity guarantees. The test does not by itself establish behavior during database failure, sustained overload, or a rolling deployment under traffic.

## Legacy Database Migration Verification — 2026-10-26

### Environment and method
- Database: PostgreSQL, running locally through Docker Compose
- Test database: `hoplid_migration_check` (disposable)
- Starting schema: legacy `orders` table with `id`, `user_id`, `status`, and `created_at`
- Test data: one representative legacy order with status `pending`
- Migration tool: Alembic
- Migration command: `./.venv/bin/python -m alembic -c /tmp/hoplid-migration-check.ini upgrade head`

### Results

| Check | Observed result |
|---|---|
| Migration `0dcdba84e47f` | Passed |
| Migration `c2ee75790b23` | Passed |
| Final Alembic revision | `c2ee75790b23` |
| Existing order preserved | Yes |
| Existing order status preserved | `pending` |
| New fields backfilled | Yes |
| Unique constraint on `(user_id, idempotency_key)` | Present |
| Duplicate user/idempotency-key insertion | Prevented |
| Number of rows for the tested key after duplicate attempt | 1 |

### Interpretation and limitations

The migration chain completed successfully against a disposable PostgreSQL database initialized with the assessment's basic legacy schema. The representative legacy row retained its ID, user ID, status, and creation timestamp. The migration populated the new fields, and a duplicate-key insertion was prevented by the database unique constraint.

This was a focused migration verification using one representative legacy row. It does not establish behavior for large datasets, malformed or unusual legacy records, concurrent writes during migration, or application rollback following a failed deployment. The test was performed against the disposable `hoplid_migration_check` database, not the active `hoplid_legacy` database.

## Migration Rollback Verification — 2026-10-26

### Method
- Database: disposable local PostgreSQL database `hoplid_migration_check`
- Starting state: both Alembic migrations applied
- Procedure: downgrade to `base`, inspect the restored schema and original row, then upgrade to `head` again

### Results
| Check | Observed result |
|---|---|
| Downgrade from `c2ee75790b23` to `base` | Passed |
| Original order preserved after downgrade | Yes |
| Original four-column schema restored | Yes |
| `user_id` restored to UUID and NOT NULL | Yes |
| `status` restored to TEXT and NOT NULL | Yes |
| `created_at` restored to NOT NULL with `NOW()` default | Yes |
| Upgrade to `head` after downgrade | Passed |
| Final Alembic revision | `c2ee75790b23` |

### Limitations
The rollback test used one representative legacy row in a disposable database. It does not prove that downgrade is safe for all possible production data or that application rollback is safe after a failed deployment. The test does not cover concurrent writes during migration or recovery from a partially completed external deployment.

## Repeat Kubernetes API Load Test — 2026-10-26

### Environment and method
- Deployment: `hoplid-api` on local Docker Desktop Kubernetes
- Database: PostgreSQL
- Access path: Kubernetes Service via local port-forward on `127.0.0.1:8000`
- Load-test script: `loadtest/load_test.py`
- Reproduction command:
  `./.venv/bin/python loadtest/load_test.py --base-url http://127.0.0.1:8000 --requests 200 --concurrency 20`
- Requests: 200 unique order creation requests
- Client concurrency: 20 worker threads

### Results

| Metric | Observed result |
|---|---:|
| Total duration | 7.93 seconds |
| Throughput | 25.22 requests/second |
| Successful HTTP responses (2xx) | 200 |
| Failed requests | 0 |
| Error rate | 0.00% |
| p50 latency | 598.57 ms |
| p95 latency | 2,590.64 ms |
| p99 latency | 2,691.80 ms |

### Kubernetes observations
- HPA CPU target: 2% / 70%
- Minimum and maximum replicas: 2 and 5
- Replicas observed after the test: 2
- Pod CPU: 2 millicores per pod at the time of inspection
- Pod memory: 60 MiB and 63 MiB
- Pod restarts: 0

### Interpretation and limitations
All 200 requests succeeded in this run, and both API pods remained ready with no observed restarts. CPU utilization stayed well below the HPA target, so scale-up was not expected or demonstrated. The p95 and p99 latencies were substantially higher than the median, indicating a slower tail of requests that warrants further investigation. This test does not identify the cause of that latency and does not establish production capacity or behavior during sustained overload, database failure, or rolling deployment under traffic.

The earlier load-test run above is retained as a separate historical measurement. Differences between runs may reflect runtime and environment variability; these results should not be interpreted as a controlled performance comparison.

## Isolated Database Connection-Pool Pressure Test — 2026-10-26

### Environment and method
- Database: local PostgreSQL test database `hoplid_test`
- Test script: `scripts/db_pool_pressure.py`
- SQLAlchemy pool size: 2 connections
- Maximum overflow connections: 0
- Connection acquisition timeout: 1 second
- Database operation: `SELECT 1`
- Safety: script requires an explicit `DATABASE_URL` and refuses to run unless the target database is `hoplid_test`
- Writes: none; the test does not modify database records

### Reproduction command
Set `DATABASE_URL` to the dedicated local test database, then run:

`./.venv/bin/python scripts/db_pool_pressure.py`

### Results

| Check | Observed result |
|---|---|
| Database safety guard | Passed; target was `hoplid_test` |
| First connection held | Passed |
| Second connection acquired | Passed |
| Third connection acquisition | Timed out as expected |
| Observed timeout | 1.000 second |
| Database writes | None |
| Test result | Passed |

### Interpretation and limitations
The test reproduces SQLAlchemy connection-pool exhaustion in a standalone engine configured with two connections, no overflow, and a one-second acquisition timeout. It confirms that an additional connection request times out when both available pool connections are checked out.

This is an isolated pool test, not a test of the running API's own connection pool. It does not establish the API's HTTP response or recovery behavior during pool exhaustion, nor does it demonstrate PostgreSQL server-wide connection exhaustion. The test does not modify application pool settings or the active `hoplid_legacy` database.

### Kubernetes Service Availability During Pod Replacement — 2026-10-26

**Environment**
- Cluster: Docker Desktop Kubernetes
- Deployment: `hoplid-api`
- Desired replicas: 2
- Probe endpoint: `http://hoplid-api/health`
- Probe location: temporary in-cluster pod using `curlimages/curl:8.10.1`

**Procedure**
1. Confirmed both API replicas were Ready.
2. Started an in-cluster health monitor targeting the Kubernetes Service DNS name.
3. The monitor issued 300 HTTP health requests at approximately 200 ms intervals, with a two-second request timeout.
4. Observed the monitor's final output and checked the API pods and Service endpoints.

**Results**
- Requests attempted: 300
- Recorded failures: 0
- Error rate: 0%
- Final API replicas: 2 Ready
- Final Service endpoints: 2

**Interpretation**

All 300 health requests recorded by the probe completed without a reported failure. Kubernetes also maintained two Ready API replicas and two Service endpoints after pod replacement.

**Limitation**

The available terminal output does not establish the exact timing of the pod deletion relative to the monitoring interval. Therefore, this run demonstrates successful Service health checks and replica recovery, but does not conclusively establish zero failed requests during the exact pod-termination window. A timestamped, synchronized repeat would provide stronger evidence of termination-time availability.

This is a local-cluster test and does not establish production availability guarantees.

## Graceful Drain and Request Rejection Test — 2026-10-26

### Objective
Verify that the API transitions to a draining state, reports itself as not ready, and rejects new application requests after an authorized drain request.

### Environment
- Docker image: `hoplid-api:local`
- Temporary container: `hoplid-drain-test`
- Test address: `127.0.0.1:18000`
- Database: `hoplid`
- Drain authorization: `X-Drain-Token` header

### Procedure and Results

| Step | Request | Observed result | Outcome |
|---|---|---|---|
| 1 | `GET /health/ready` before draining | `200 OK`, database reported `ok` | PASS |
| 2 | `POST /internal/drain` with valid drain token | `200 OK`, status `draining` | PASS |
| 3 | `GET /health/ready` after draining | `503 Service Unavailable` | PASS |
| 4 | `POST /api/orders` after draining | `503 Service Unavailable` | PASS |

### Conclusion
The application-level drain sequence behaved as expected. Readiness changed from healthy to unavailable, and a new order request was rejected after draining began. The temporary test container was removed after testing.

### Limitations
This test did not generate concurrent traffic during termination or verify completion of in-flight order requests. It also did not independently measure how quickly Kubernetes removes a draining pod from service endpoints. Those behaviors require separate validation before claiming complete graceful-shutdown guarantees.

The drain token used in this local assessment is a development value and must be replaced with a securely generated secret before production use.

## Idempotency Concurrency Test — 2026-10-26

### Objective
Verify that concurrent duplicate order submissions do not create duplicate records, and that reusing an idempotency key with a different payload is rejected.

### Environment
- API: local Docker Compose test API at `http://localhost:8001`
- Database: `hoplid_test`
- Concurrent workers: 10
- Requests: 10 concurrent submissions using the same unique user, idempotency key, and payload

### Results

| Check | Observed result | Outcome |
|---|---|---|
| API health | `GET /health` returned 200 | PASS |
| Concurrent duplicate requests | 10 responses returned HTTP 201 | PASS |
| Returned order identity | All 10 responses contained the same order ID | PASS |
| Same key with changed payload | HTTP 409 Conflict | PASS |
| Database row count for test user/key | Exactly 1 row | PASS |
| Test data cleanup | Targeted cleanup completed | PASS |

### Conclusion
The test demonstrated idempotent behavior for 10 concurrent requests using the same key and payload. Reusing that key with a different payload returned HTTP 409, and the database contained exactly one matching order after the concurrent requests.

### Limitations
This was one local test run with 10 concurrent workers against the Docker Compose test API. It does not establish behavior under all concurrency levels, database outages, or a crash after transaction commit but before the response reaches the client. The test API exposed `/health`; the newer readiness and liveness endpoints were not present in that older test container.
