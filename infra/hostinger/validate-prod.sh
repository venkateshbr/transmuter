#!/usr/bin/env bash
set -euo pipefail

PROD_LOCAL_BASE_URL="${PROD_LOCAL_BASE_URL:-http://127.0.0.1:4301}"
PROD_PUBLIC_BASE_URL="${PROD_PUBLIC_BASE_URL:-https://transmuter.ishirock.tech}"
VALIDATE_LOCAL="${VALIDATE_LOCAL:-0}"
CURL_INSECURE_FLAG=()

if [[ "${ALLOW_INSECURE_TLS:-0}" == "1" ]]; then
  CURL_INSECURE_FLAG=(-k)
fi

if [[ "${VALIDATE_LOCAL}" == "1" ]]; then
  echo "Validating production on the VPS loopback at ${PROD_LOCAL_BASE_URL}."
  curl -fsS "${PROD_LOCAL_BASE_URL}/health" >/dev/null
  curl -fsS "${PROD_LOCAL_BASE_URL}/api/health" >/dev/null
else
  echo "Skipping VPS loopback validation. Set VALIDATE_LOCAL=1 when running on the Hostinger VPS."
fi

echo "Validating production publicly at ${PROD_PUBLIC_BASE_URL}."
if [[ "${#CURL_INSECURE_FLAG[@]}" -gt 0 ]]; then
  curl "${CURL_INSECURE_FLAG[@]}" -fsS "${PROD_PUBLIC_BASE_URL}/health" >/dev/null
  curl "${CURL_INSECURE_FLAG[@]}" -fsS "${PROD_PUBLIC_BASE_URL}/api/health" >/dev/null
else
  curl -fsS "${PROD_PUBLIC_BASE_URL}/health" >/dev/null
  curl -fsS "${PROD_PUBLIC_BASE_URL}/api/health" >/dev/null
fi

echo "Production validation passed."
