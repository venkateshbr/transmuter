#!/usr/bin/env bash
set -euo pipefail

PROD_LOCAL_BASE_URL="${PROD_LOCAL_BASE_URL:-http://127.0.0.1:4301}"
PROD_PUBLIC_BASE_URL="${PROD_PUBLIC_BASE_URL:-https://transmuter.ishirock.tech}"

echo "Validating production locally at ${PROD_LOCAL_BASE_URL}."
curl -fsS "${PROD_LOCAL_BASE_URL}/health" >/dev/null
curl -fsS "${PROD_LOCAL_BASE_URL}/api/health" >/dev/null

echo "Validating production publicly at ${PROD_PUBLIC_BASE_URL}."
curl -fsS "${PROD_PUBLIC_BASE_URL}/health" >/dev/null
curl -fsS "${PROD_PUBLIC_BASE_URL}/api/health" >/dev/null

echo "Production validation passed."
