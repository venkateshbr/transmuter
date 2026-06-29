#!/usr/bin/env bash
set -euo pipefail

PROD_LOCAL_BASE_URL="${PROD_LOCAL_BASE_URL:-http://127.0.0.1:4301}"
PROD_PUBLIC_BASE_URL="${PROD_PUBLIC_BASE_URL:-https://transmuter.ishirock.tech}"
VALIDATE_LOCAL="${VALIDATE_LOCAL:-0}"

check_url() {
  local url="$1"
  local attempts="${2:-30}"
  local delay="${3:-10}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if curl -fsS "${url}" >/dev/null; then
      return 0
    fi
    sleep "${delay}"
  done
  echo "Health check failed after ${attempts} attempts: ${url}" >&2
  return 1
}

if [[ "${VALIDATE_LOCAL}" == "1" ]]; then
  echo "Validating production local bind at ${PROD_LOCAL_BASE_URL}."
  check_url "${PROD_LOCAL_BASE_URL}/health" 6 5
  check_url "${PROD_LOCAL_BASE_URL}/api/health" 6 5
fi

echo "Validating production publicly at ${PROD_PUBLIC_BASE_URL}."
check_url "${PROD_PUBLIC_BASE_URL}/health"
check_url "${PROD_PUBLIC_BASE_URL}/api/health"

echo "Production validation passed."
