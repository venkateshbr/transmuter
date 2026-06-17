#!/usr/bin/env bash
set -euo pipefail

DEV_LOCAL_BASE_URL="${DEV_LOCAL_BASE_URL:-http://127.0.0.1:4302}"
DEV_PUBLIC_BASE_URL="${DEV_PUBLIC_BASE_URL:-https://transmuter-dev.ishirock.tech}"
CURL_INSECURE_FLAG=()

if [[ "${ALLOW_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_INSECURE_FLAG=(-k)
fi

echo "Validating dev locally at ${DEV_LOCAL_BASE_URL}."
curl -fsS "${DEV_LOCAL_BASE_URL}/health" >/dev/null
curl -fsS "${DEV_LOCAL_BASE_URL}/api/health" >/dev/null

echo "Validating dev publicly at ${DEV_PUBLIC_BASE_URL}."
curl "${CURL_INSECURE_FLAG[@]}" -fsS "${DEV_PUBLIC_BASE_URL}/health" >/dev/null
curl "${CURL_INSECURE_FLAG[@]}" -fsS "${DEV_PUBLIC_BASE_URL}/api/health" >/dev/null

echo "Dev validation passed."
