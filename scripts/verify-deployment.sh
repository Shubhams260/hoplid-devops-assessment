#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-default}"
BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Checking Kubernetes rollout..."
kubectl rollout status deployment/hoplid-api \
  -n "$NAMESPACE" --timeout=120s

echo "Checking API health..."
curl --fail --silent --show-error "$BASE_URL/health"
echo
curl --fail --silent --show-error "$BASE_URL/health/live"
echo
curl --fail --silent --show-error "$BASE_URL/health/ready"
echo

KEY="verify-$(date +%s)-$$"
USER_ID="verify-user-$(date +%s)-$$"
BODY="{\"user_id\":\"$USER_ID\",\"vendor_id\":\"verify-vendor\",\"items\":[{\"item_id\":\"verify-item\",\"quantity\":1}]}"
CHANGED_BODY="{\"user_id\":\"$USER_ID\",\"vendor_id\":\"verify-vendor\",\"items\":[{\"item_id\":\"verify-item\",\"quantity\":2}]}"

TMP1="$(mktemp)"
TMP2="$(mktemp)"
TMP3="$(mktemp)"
trap 'rm -f "$TMP1" "$TMP2" "$TMP3"' EXIT

post_order() {
  local body="$1"
  local output="$2"
  curl --silent --show-error \
    -o "$output" -w '%{http_code}' \
    -X POST "$BASE_URL/api/orders" \
    -H "Content-Type: application/json" \
    -H "Idempotency-Key: $KEY" \
    -d "$body"
}

echo "Creating a test order..."
STATUS1="$(post_order "$BODY" "$TMP1")"
if [[ "$STATUS1" != "201" ]]; then
  echo "FAIL: initial order returned HTTP $STATUS1"
  cat "$TMP1"
  exit 1
fi

echo "Retrying the identical request..."
STATUS2="$(post_order "$BODY" "$TMP2")"
if [[ "$STATUS2" != "200" && "$STATUS2" != "201" ]]; then
  echo "FAIL: retry returned HTTP $STATUS2"
  cat "$TMP2"
  exit 1
fi

ID1="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$TMP1")"
ID2="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["id"])' "$TMP2")"

if [[ "$ID1" != "$ID2" ]]; then
  echo "FAIL: retry returned a different order ID"
  exit 1
fi

echo "Reusing the key with a changed payload..."
STATUS3="$(post_order "$CHANGED_BODY" "$TMP3")"
if [[ "$STATUS3" != "409" ]]; then
  echo "FAIL: changed payload returned HTTP $STATUS3; expected 409"
  cat "$TMP3"
  exit 1
fi

echo "PASS: rollout, health checks, idempotent retry, and payload-conflict checks passed."
echo "Order ID verified: $ID1"
