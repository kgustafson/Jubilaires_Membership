#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTEST="${PROJECT_ROOT}/.venv/bin/pytest"

if [[ ! -x "${PYTEST}" ]]; then
  echo "Smoke tests failed: pytest was not found in ${PROJECT_ROOT}/.venv." >&2
  echo "Install test dependencies with:" >&2
  echo "  ${PROJECT_ROOT}/.venv/bin/pip install -r ${PROJECT_ROOT}/requirements-dev.txt" >&2
  exit 1
fi

echo "Running Jubilaires Membership smoke tests..."
echo "App URL: ${JUBILAIRES_SMOKE_BASE_URL:-http://127.0.0.1:8091}"
echo

cd "${PROJECT_ROOT}"
exec "${PYTEST}" -v -p no:cacheprovider tests "$@"
