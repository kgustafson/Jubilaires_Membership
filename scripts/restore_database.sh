#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${JUBILAIRES_BACKUP_DIR:-${PROJECT_ROOT}/backups}"
DB_CONTAINER="${JUBILAIRES_DB_CONTAINER:-jubilaires_membership_db}"
DB_NAME="${JUBILAIRES_DB_NAME:-jubilaires_membership}"
DB_USER="${JUBILAIRES_DB_USER:-admin}"
CONFIRM_RESTORE="0"

usage() {
  echo "Usage: $0 [--yes] <backup-file-or-name>" >&2
  echo "Examples:" >&2
  echo "  $0 2026-05-08-001.dump" >&2
  echo "  $0 --yes ${BACKUP_DIR}/2026-05-08-001.dump" >&2
}

if [[ "${1:-}" == "--yes" || "${1:-}" == "-y" ]]; then
  CONFIRM_RESTORE="1"
  shift
fi

if [[ $# -ne 1 ]]; then
  usage
  exit 2
fi

backup_input="$1"
if [[ "${backup_input}" == */* ]]; then
  backup_path="${backup_input}"
else
  backup_path="${BACKUP_DIR}/${backup_input}"
fi

if [[ ! -f "${backup_path}" ]]; then
  echo "Restore failed: backup file not found: ${backup_path}" >&2
  exit 1
fi

if [[ "${backup_path}" != *.dump ]]; then
  echo "Restore failed: expected a .dump backup file." >&2
  exit 1
fi

if [[ "${CONFIRM_RESTORE}" != "1" ]]; then
  echo "This will replace data in database '${DB_NAME}' using:"
  echo "  ${backup_path}"
  read -r -p "Type RESTORE to continue: " answer
  if [[ "${answer}" != "RESTORE" ]]; then
    echo "Restore cancelled."
    exit 0
  fi
fi

echo "Restoring database '${DB_NAME}' from ${backup_path}"
docker exec -i "${DB_CONTAINER}" pg_restore \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --clean \
  --if-exists \
  --no-owner \
  --no-privileges < "${backup_path}"

echo "Restore complete."
