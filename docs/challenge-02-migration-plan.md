# Challenge 02 — Backward-compatible database evolution

## Actual implementation in this repository

The current Alembic history adds order idempotency columns and the unique constraint `(user_id, idempotency_key)`. Challenge 02 adds revision `76bdc2ef9a10`, which expands the schema with nullable `status_code`, backfills existing statuses, and preserves the original text `status` column for compatibility.

Status code mapping:

| Code | Recognized legacy status |
|---:|---|
| 0 | Unknown/unmapped value; the original text is preserved |
| 1 | `pending` |
| 2 | `confirmed` |
| 3 | `preparing` |
| 4 | `ready` |
| 5 | `completed` |
| 6 | `cancelled` |

The new application writes both `status` and `status_code` for newly created orders. The code column remains nullable because an older application version may still insert orders without knowing about it. During this compatibility phase, the text column remains available and must not be dropped.

## Expand-and-contract release plan

1. **Expand:** apply the additive Alembic migration before deploying code that writes `status_code`. Existing application instances continue to use the text `status` column.
2. **Backfill:** the migration maps recognized status strings to codes and maps unknown legacy strings to `0`. It does not overwrite the original text, so invalid legacy values remain inspectable.
3. **Overlap:** deploy the new app gradually. Old versions can write rows where `status_code` is NULL; new versions dual-write the text and numeric code. Keep the text column as the compatibility source until all old binaries are retired.
4. **Verify:** CI migrates a disposable database containing recognized and unrecognized legacy statuses, then asserts the text is preserved and the codes are populated.
5. **Contract later:** a future release may switch all reads to the numeric representation and stop writing text only after every version has been made compatible. Dropping the legacy text column is deliberately not part of this migration.

## Idempotency and concurrent requests

PostgreSQL remains the durable source of truth. The existing uniqueness constraint `UNIQUE (user_id, idempotency_key)` enforces idempotency under concurrent inserts. The API handles a uniqueness race by rolling back and re-reading the matching row; same payload returns the existing order and a different payload returns HTTP 409.

Historical orders do not have client-generated idempotency keys. The existing Challenge 01 migration assigns `legacy:<order-id>` per row instead of inventing one shared key. The CI migration job checks this behavior and verifies the request hash backfill.

## Failed deployment after successful schema migration

- Retain additive, backward-compatible schema changes.
- Roll the Kubernetes Deployment back to the previous image if the old version is compatible with the expanded schema.
- Do not automatically downgrade the database: that is a separate operation and can destroy information if newer code has written data that depends on the new schema.
- Prefer fixing forward. Contract/drop operations should be deferred until the old application version is no longer a rollback target.

## Concurrency-safe constraint introduction

The existing Challenge 01 migration creates the unique constraint after assigning each legacy order a distinct key. The Challenge 02 status migration does not weaken that constraint. The CI migration job begins from the assessment's simplified legacy schema and verifies the complete Alembic chain on a clean disposable PostgreSQL database. For large production tables, index creation and lock duration require a separately reviewed online-migration plan.

## WebSockets, draining and retries

This prototype does not implement a WebSocket endpoint. For a production extension, clients should reconnect using bounded exponential backoff with jitter, re-authenticate, and resubscribe to order updates; after reconnect, they should reconcile current state from the durable API. During pod termination, mark the pod unready, reject new work, allow in-flight requests to finish within the grace period, and retry uncertain order submissions with the same idempotency key.

## Test limitations

The CI migration test uses a small representative legacy dataset. It proves the migration chain, a recognized status, an unmapped status, and idempotency-field backfill; it does not prove performance on a large production table, concurrent schema changes, or production zero-downtime behavior.
