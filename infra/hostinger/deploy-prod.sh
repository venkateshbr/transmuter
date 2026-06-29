#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"
export HOSTINGER_DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-/docker/transmuter}"
export TRANSMUTER_COMPOSE_PROJECT="${TRANSMUTER_COMPOSE_PROJECT:-transmuter-hostinger}"
export HOSTINGER_PROJECT_NAME="${HOSTINGER_PROJECT_NAME:-${TRANSMUTER_COMPOSE_PROJECT}}"
export HOSTINGER_VPS_ID="${HOSTINGER_VPS_ID:-1695814}"
export HOSTINGER_PUBLIC_IP="${HOSTINGER_PUBLIC_IP:-76.13.208.106}"
export HOSTINGER_STOP_PROJECTS="${HOSTINGER_STOP_PROJECTS:-transmuter transmuter-hostinger}"
export TRANSMUTER_API_IMAGE="${TRANSMUTER_API_IMAGE:-transmuter-api:hostinger}"
export TRANSMUTER_WEB_IMAGE="${TRANSMUTER_WEB_IMAGE:-transmuter-web:hostinger}"
export APP_PUBLIC_URL="${APP_PUBLIC_URL:-https://transmuter.ishirock.tech}"
export TRANSMUTER_ENVIRONMENT="${TRANSMUTER_ENVIRONMENT:-production}"
export TRAEFIK_HOSTNAME="${TRAEFIK_HOSTNAME:-transmuter.ishirock.tech}"
export TRAEFIK_ROUTER_NAME="${TRAEFIK_ROUTER_NAME:-transmuter-web}"
export TRAEFIK_SERVICE_NAME="${TRAEFIK_SERVICE_NAME:-transmuter-web}"
export TRANSMUTER_WEB_BIND="${TRANSMUTER_WEB_BIND:-127.0.0.1:4301}"
export SUPABASE_SCHEMA="${SUPABASE_SCHEMA:-transmuter}"
export DB_SCHEMA="${DB_SCHEMA:-transmuter}"

exec "${SCRIPT_DIR}/deploy-remote.sh" "$@"
