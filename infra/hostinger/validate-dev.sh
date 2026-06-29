#!/usr/bin/env bash
set -euo pipefail

DEV_LOCAL_BASE_URL="${DEV_LOCAL_BASE_URL:-http://127.0.0.1:4302}"
DEV_PUBLIC_BASE_URL="${DEV_PUBLIC_BASE_URL:-https://transmuter-dev.ishirock.tech}"
VALIDATE_LOCAL="${VALIDATE_LOCAL:-0}"
CURL_INSECURE_FLAG=()

if [[ "${ALLOW_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_INSECURE_FLAG=(-k)
fi

if [[ "${VALIDATE_LOCAL}" == "1" ]]; then
  echo "Validating dev on the VPS loopback at ${DEV_LOCAL_BASE_URL}."
  curl -fsS "${DEV_LOCAL_BASE_URL}/health" >/dev/null
  curl -fsS "${DEV_LOCAL_BASE_URL}/api/health" >/dev/null
else
  echo "Skipping VPS loopback validation. Set VALIDATE_LOCAL=1 when running on the Hostinger VPS."
fi

echo "Validating dev publicly at ${DEV_PUBLIC_BASE_URL}."
if [[ "${#CURL_INSECURE_FLAG[@]}" -gt 0 ]]; then
  curl "${CURL_INSECURE_FLAG[@]}" -fsS "${DEV_PUBLIC_BASE_URL}/health" >/dev/null
  curl "${CURL_INSECURE_FLAG[@]}" -fsS "${DEV_PUBLIC_BASE_URL}/api/health" >/dev/null
else
  curl -fsS "${DEV_PUBLIC_BASE_URL}/health" >/dev/null
  curl -fsS "${DEV_PUBLIC_BASE_URL}/api/health" >/dev/null
fi

echo "Dev validation passed."
