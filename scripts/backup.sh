#!/usr/bin/env bash
set -euo pipefail

DATE="$(date -u +%Y%m%d_%H%M%S)"
BACKUP_DIR="$(mktemp -d "/tmp/veridis-backup-${DATE}.XXXXXX")"
S3_BUCKET="${S3_BACKUP_BUCKET:-s3://veridis-backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

cleanup() {
  rm -rf "${BACKUP_DIR}"
}
trap cleanup EXIT

notify() {
  local message="$1"
  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    curl -fsS -X POST "${SLACK_WEBHOOK_URL}" \
      -H "Content-type: application/json" \
      --data "{\"text\":\"${message}\"}" >/dev/null || true
  fi
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

require_command pg_dump
require_command gzip
require_command aws

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required." >&2
  exit 1
fi

echo "Starting VERIDIS backup ${DATE}"
mkdir -p "${BACKUP_DIR}"

pg_dump "${DATABASE_URL}" --no-owner --no-privileges | gzip > "${BACKUP_DIR}/postgres.sql.gz"

if [[ -n "${REDIS_URL:-}" ]] && command -v redis-cli >/dev/null 2>&1; then
  redis-cli -u "${REDIS_URL}" --rdb "${BACKUP_DIR}/redis.rdb"
fi

aws s3 sync "${BACKUP_DIR}" "${S3_BUCKET}/${DATE}/" --only-show-errors

cutoff_epoch="$(date -u -d "${RETENTION_DAYS} days ago" +%s)"
aws s3 ls "${S3_BUCKET}/" | awk '{print $2}' | while read -r prefix; do
  backup_name="${prefix%/}"
  if [[ "${backup_name}" =~ ^[0-9]{8}_[0-9]{6}$ ]]; then
    backup_epoch="$(date -u -d "${backup_name:0:4}-${backup_name:4:2}-${backup_name:6:2} ${backup_name:9:2}:${backup_name:11:2}:${backup_name:13:2}" +%s)"
    if [[ "${backup_epoch}" -lt "${cutoff_epoch}" ]]; then
      aws s3 rm "${S3_BUCKET}/${backup_name}/" --recursive --only-show-errors
    fi
  fi
done

notify "VERIDIS backup completed: ${DATE}"
echo "Backup completed: ${DATE}"
