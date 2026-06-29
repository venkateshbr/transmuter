#!/usr/bin/env bash
set -euo pipefail

DEV_LOCAL_BASE_URL="${DEV_LOCAL_BASE_URL:-http://127.0.0.1:4302}"
DEV_PUBLIC_BASE_URL="${DEV_PUBLIC_BASE_URL:-https://transmuter-dev.ishirock.tech}"
VALIDATE_LOCAL="${VALIDATE_LOCAL:-0}"
CURL_INSECURE_FLAG=()

if [[ "${ALLOW_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_INSECURE_FLAG=(-k)
fi

check_url() {
  local url="$1"
  local attempts="${2:-30}"
  local delay="${3:-10}"
  local i
  for ((i = 1; i <= attempts; i++)); do
    if [[ "${ALLOW_INSECURE_TLS:-0}" == "1" ]]; then
      curl -k -fsS "${url}" >/dev/null && return 0
    elif curl -fsS "${url}" >/dev/null; then
      return 0
    fi
    sleep "${delay}"
  done
  echo "Health check failed after ${attempts} attempts: ${url}" >&2
  return 1
}

if [[ "${VALIDATE_LOCAL}" == "1" ]]; then
  echo "Validating dev local bind at ${DEV_LOCAL_BASE_URL}."
  check_url "${DEV_LOCAL_BASE_URL}/health" 6 5
  check_url "${DEV_LOCAL_BASE_URL}/api/health" 6 5
fi

echo "Validating dev publicly at ${DEV_PUBLIC_BASE_URL}."
check_url "${DEV_PUBLIC_BASE_URL}/health"
check_url "${DEV_PUBLIC_BASE_URL}/api/health"

echo "Dev validation passed."
