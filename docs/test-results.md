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
