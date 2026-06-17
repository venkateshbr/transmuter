#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env.dev}"
export HOSTINGER_DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-/docker/transmuter-dev}"
export TRANSMUTER_COMPOSE_PROJECT="${TRANSMUTER_COMPOSE_PROJECT:-transmuter-dev-hostinger}"
export HOSTINGER_STOP_PROJECTS="${HOSTINGER_STOP_PROJECTS:-${TRANSMUTER_COMPOSE_PROJECT}}"
export TRANSMUTER_API_IMAGE="${TRANSMUTER_API_IMAGE:-transmuter-api:hostinger-dev}"
export TRANSMUTER_WEB_IMAGE="${TRANSMUTER_WEB_IMAGE:-transmuter-web:hostinger-dev}"
export APP_PUBLIC_URL="${APP_PUBLIC_URL:-https://transmuter-dev.ishirock.tech}"
export TRANSMUTER_ENVIRONMENT="${TRANSMUTER_ENVIRONMENT:-development}"
export TRAEFIK_HOSTNAME="${TRAEFIK_HOSTNAME:-transmuter-dev.ishirock.tech}"
export TRAEFIK_ROUTER_NAME="${TRAEFIK_ROUTER_NAME:-transmuter-dev-web}"
export TRAEFIK_SERVICE_NAME="${TRAEFIK_SERVICE_NAME:-transmuter-dev-web}"
export TRANSMUTER_WEB_BIND="${TRANSMUTER_WEB_BIND:-127.0.0.1:4302}"
export SUPABASE_SCHEMA="${SUPABASE_SCHEMA:-transmuter_dev}"
export DB_SCHEMA="${DB_SCHEMA:-transmuter_dev}"
export RUN_DB_SCHEMA_MIGRATION="${RUN_DB_SCHEMA_MIGRATION:-0}"

exec "${SCRIPT_DIR}/deploy.sh" "$@"
