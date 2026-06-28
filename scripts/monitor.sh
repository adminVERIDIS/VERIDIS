#!/usr/bin/env bash
set -euo pipefail

ENDPOINTS=(${MONITOR_ENDPOINTS:-"https://veridis.fr/api/health https://api.veridis.fr/health"})
TIMEOUT_SECONDS="${MONITOR_TIMEOUT_SECONDS:-10}"

notify() {
  local message="$1"
  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -fsS -X POST "${SLACK_WEBHOOK_URL}" \
      -H "Content-type: application/json" \
      --data "{\"text\":\"${message}\"}" >/dev/null || true
  fi
}

for endpoint in "${ENDPOINTS[@]}"; do
  status="$(curl -sS -o /dev/null -w "%{http_code}" --max-time "${TIMEOUT_SECONDS}" "${endpoint}" || echo "000")"
  if [[ "${status}" != "200" ]]; then
    notify "VERIDIS ALERT: ${endpoint} returned ${status}"
    echo "ALERT ${endpoint} ${status}" >&2
  else
    echo "OK ${endpoint}"
  fi
done
