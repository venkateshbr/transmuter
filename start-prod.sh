#!/usr/bin/env bash
set -euo pipefail

export TRANSMUTER_API_URL="${TRANSMUTER_API_URL:-/api}"

docker compose -f infra/docker-compose.prod.yml --env-file .env up --build
