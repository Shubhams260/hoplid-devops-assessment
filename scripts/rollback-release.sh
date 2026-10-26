#!/usr/bin/env bash
# Application-only rollback. Does not downgrade or reverse database migrations.
set -Eeuo pipefail
NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT="${DEPLOYMENT:-hoplid-api}"
TIMEOUT="${TIMEOUT:-120s}"

echo "Current revision:"
kubectl rollout history "deployment/${DEPLOYMENT}" -n "$NAMESPACE"
echo "Rolling back application Deployment to previous revision..."
kubectl rollout undo "deployment/${DEPLOYMENT}" -n "$NAMESPACE"
kubectl rollout status "deployment/${DEPLOYMENT}" -n "$NAMESPACE" --timeout="$TIMEOUT"
echo "Rollback completed. Run ./scripts/verify-deployment.sh to check readiness and orders."
echo "IMPORTANT: the database schema is unchanged; roll back only to an application version compatible with the current schema."
