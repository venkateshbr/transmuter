#!/usr/bin/env bash
set -euo pipefail

docker compose -f infra/docker-compose.prod.yml --env-file .env down
