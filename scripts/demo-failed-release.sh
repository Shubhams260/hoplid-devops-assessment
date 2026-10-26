#!/usr/bin/env bash
# Safe, local demonstration using a deliberately unavailable image.
set -Eeuo pipefail
NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT="${DEPLOYMENT:-hoplid-api}"
CONTAINER="${CONTAINER:-hoplid-api}"
BAD_IMAGE="${BAD_IMAGE:-hoplid-api:deliberately-missing-for-recovery-demo}"
TIMEOUT="${TIMEOUT:-45s}"

if [[ "${ALLOW_FAILURE_DEMO:-}" != "yes" ]]; then
  echo "This temporarily changes the selected Kubernetes Deployment."
  echo "Run only on the local assessment cluster with:"
  echo "  ALLOW_FAILURE_DEMO=yes ./scripts/demo-failed-release.sh"
  exit 2
fi

ORIGINAL_IMAGE="$(kubectl get deployment "$DEPLOYMENT" -n "$NAMESPACE" \
  -o "jsonpath={.spec.template.spec.containers[?(@.name==\"${CONTAINER}\")].image}")"
if [[ -z "$ORIGINAL_IMAGE" ]]; then
  echo "Could not determine image for container ${CONTAINER}."
  exit 1
fi

restore() {
  echo "Restoring original image ${ORIGINAL_IMAGE}..."
  kubectl set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${ORIGINAL_IMAGE}" -n "$NAMESPACE"
  kubectl rollout status "deployment/${DEPLOYMENT}" -n "$NAMESPACE" --timeout=120s
}
trap restore EXIT

echo "Original image: ${ORIGINAL_IMAGE}"
echo "Injecting unavailable image: ${BAD_IMAGE}"
kubectl set image "deployment/${DEPLOYMENT}" "${CONTAINER}=${BAD_IMAGE}" -n "$NAMESPACE"

set +e
kubectl rollout status "deployment/${DEPLOYMENT}" -n "$NAMESPACE" --timeout="$TIMEOUT"
ROLLOUT_RC=$?
set -e

echo "Injected rollout exit code: ${ROLLOUT_RC} (non-zero is expected)"
kubectl get pods -n "$NAMESPACE" -l app=hoplid-api -o wide || true
kubectl describe deployment "$DEPLOYMENT" -n "$NAMESPACE" || true
if [[ "$ROLLOUT_RC" -eq 0 ]]; then
  echo "WARNING: rollout reported success; verify the failure-injection outcome manually."
else
  echo "Failure detected. Exit trap now restores the original image."
fi
