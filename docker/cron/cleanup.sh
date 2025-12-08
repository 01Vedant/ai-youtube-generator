#!/bin/bash
# Cleanup script wrapper for cron/K8s CronJob
# Calls the retention cleanup endpoint

set -e

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"

echo "[$(date)] Starting retention cleanup..."

# Call retention endpoint
if [ -n "$ADMIN_TOKEN" ]; then
  curl -X POST "$BACKEND_URL/admin/retention/run" \
    -H "Authorization: Bearer $ADMIN_TOKEN" \
    -H "Content-Type: application/json" \
    -s -o /tmp/retention_result.json \
    -w "HTTP %{http_code}\n"
else
  curl -X POST "$BACKEND_URL/admin/retention/run" \
    -H "Content-Type: application/json" \
    -s -o /tmp/retention_result.json \
    -w "HTTP %{http_code}\n"
fi

# Log result
if [ -f /tmp/retention_result.json ]; then
  echo "[$(date)] Retention result:"
  cat /tmp/retention_result.json | python3 -m json.tool || cat /tmp/retention_result.json
  rm /tmp/retention_result.json
fi

echo "[$(date)] Retention cleanup completed"
