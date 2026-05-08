#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${JUBILAIRES_BACKUP_DIR:-${PROJECT_ROOT}/backups}"
DB_CONTAINER="${JUBILAIRES_DB_CONTAINER:-jubilaires_membership_db}"
DB_NAME="${JUBILAIRES_DB_NAME:-jubilaires_membership}"
DB_USER="${JUBILAIRES_DB_USER:-admin}"

mkdir -p "${BACKUP_DIR}"

today="$(date +%Y-%m-%d)"
ordinal=1
while true; do
  backup_name="$(printf "%s-%03d.dump" "${today}" "${ordinal}")"
  backup_path="${BACKUP_DIR}/${backup_name}"
  if [[ ! -e "${backup_path}" ]]; then
    break
  fi
  ordinal=$((ordinal + 1))
done

echo "Creating database backup: ${backup_path}"
docker exec "${DB_CONTAINER}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" -Fc > "${backup_path}"

if [[ ! -s "${backup_path}" ]]; then
  rm -f "${backup_path}"
  echo "Backup failed: pg_dump produced an empty file." >&2
  exit 1
fi

echo "Backup complete: ${backup_path}"
