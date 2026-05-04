#!/usr/bin/env bash
set -euo pipefail

export TRANSMUTER_API_URL="${TRANSMUTER_API_URL:-http://localhost:8001}"

docker compose -f infra/docker-compose.prod.yml --env-file .env up --build
