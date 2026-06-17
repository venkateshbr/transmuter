#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ENV_FILE="${ENV_FILE:-${SCRIPT_DIR}/.env}"
HOSTINGER_COMPOSE_TEMPLATE="${HOSTINGER_COMPOSE_TEMPLATE:-${REPO_ROOT}/docker-compose.hostinger.yml}"
DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-/docker/transmuter}"
REMOTE_ENV_FILE_OVERRIDE="${REMOTE_ENV_FILE:-}"
REMOTE_COMPOSE_FILE_OVERRIDE="${REMOTE_COMPOSE_FILE:-}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE_OVERRIDE:-${DEPLOY_DIR}/.env}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE_OVERRIDE:-${DEPLOY_DIR}/docker-compose.yml}"
RUN_DB_SCHEMA_MIGRATION="${RUN_DB_SCHEMA_MIGRATION:-0}"
DOCKER_BIN="${DOCKER_BIN:-docker}"

usage() {
  cat <<'USAGE'
Stage and deploy the Transmuter Hostinger bundle locally.

This script copies the required repo subsets into /docker/transmuter on this
machine, then builds and starts the Docker Compose stack from that local bundle.
No SSH is used.

Required local file:
  infra/hostinger/.env  Runtime secrets and deployment settings.
  Use infra/hostinger/.env.example as the template.

Local bundle layout:
  /docker/transmuter/docker-compose.yml  Compose entrypoint staged by this script
  /docker/transmuter/.env                Runtime env file copied from infra/hostinger/.env
  /docker/transmuter/apps/...            Minimal app bundle needed to build containers
  /docker/transmuter/domain_packs/...    API build input
  /docker/transmuter/infra/hostinger/... Hostinger helper scripts and docs

Useful environment overrides:
  ENV_FILE=/path/to/hostinger.env
  HOSTINGER_DEPLOY_DIR=/docker/transmuter
  HOSTINGER_COMPOSE_TEMPLATE=/path/to/docker-compose.hostinger.yml
  TRANSMUTER_COMPOSE_PROJECT=transmuter-hostinger
  HOSTINGER_STOP_PROJECTS="transmuter transmuter-hostinger"
  RUN_DB_SCHEMA_MIGRATION=1
  DOCKER_BIN=docker

Example:
  ./infra/hostinger/deploy.sh
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Missing ${ENV_FILE}. Copy infra/hostinger/.env.example to infra/hostinger/.env and fill in real values." >&2
  exit 1
fi

if [[ ! -f "${HOSTINGER_COMPOSE_TEMPLATE}" ]]; then
  echo "Missing compose template: ${HOSTINGER_COMPOSE_TEMPLATE}" >&2
  exit 1
fi

require_command rsync
require_command "${DOCKER_BIN}"

set -a
# shellcheck source=/dev/null
. "${ENV_FILE}"
set +a

DEPLOY_DIR="${HOSTINGER_DEPLOY_DIR:-${DEPLOY_DIR}}"
REMOTE_ENV_FILE="${REMOTE_ENV_FILE_OVERRIDE:-${DEPLOY_DIR}/.env}"
REMOTE_COMPOSE_FILE="${REMOTE_COMPOSE_FILE_OVERRIDE:-${DEPLOY_DIR}/docker-compose.yml}"
COMPOSE_PROJECT="${TRANSMUTER_COMPOSE_PROJECT:-${COMPOSE_PROJECT_NAME:-transmuter-hostinger}}"
if [[ -z "${HOSTINGER_STOP_PROJECTS:-}" ]]; then
  if [[ "${COMPOSE_PROJECT}" == "transmuter-hostinger" ]]; then
    HOSTINGER_STOP_PROJECTS="transmuter transmuter-hostinger"
  else
    HOSTINGER_STOP_PROJECTS="${COMPOSE_PROJECT}"
  fi
fi

APP_EXCLUDES=(
  --exclude ".git/"
  --exclude ".pytest_cache/"
  --exclude ".ruff_cache/"
  --exclude ".mypy_cache/"
  --exclude ".venv/"
  --exclude "node_modules/"
  --exclude ".angular/"
  --exclude "dist/"
  --exclude "coverage/"
  --exclude "*.log"
  --exclude ".env"
  --exclude ".env.local"
  --exclude ".env.*"
)

HOSTINGER_EXCLUDES=(
  --exclude ".env"
  --exclude ".env.local"
  --exclude ".env.hostinger"
  --exclude "docker-compose.yml"
)

DEPLOY_DIR_PARENT="$(dirname "${DEPLOY_DIR}")"
mkdir -p "${DEPLOY_DIR_PARENT}"
rm -rf "${DEPLOY_DIR}"
mkdir -p "${DEPLOY_DIR}/apps/api" "${DEPLOY_DIR}/apps/web" "${DEPLOY_DIR}/domain_packs" "${DEPLOY_DIR}/infra/hostinger"

echo "Staging Transmuter bundle locally into ${DEPLOY_DIR}"
echo "Compose template: ${HOSTINGER_COMPOSE_TEMPLATE}"

rsync -az --delete "${APP_EXCLUDES[@]}" \
  "${REPO_ROOT}/apps/api/" "${DEPLOY_DIR}/apps/api/"

rsync -az --delete "${APP_EXCLUDES[@]}" \
  "${REPO_ROOT}/apps/web/" "${DEPLOY_DIR}/apps/web/"

rsync -az --delete "${APP_EXCLUDES[@]}" \
  "${REPO_ROOT}/domain_packs/" "${DEPLOY_DIR}/domain_packs/"

rsync -az --delete "${HOSTINGER_EXCLUDES[@]}" \
  "${REPO_ROOT}/infra/hostinger/" "${DEPLOY_DIR}/infra/hostinger/"

cp "${HOSTINGER_COMPOSE_TEMPLATE}" "${REMOTE_COMPOSE_FILE}"
cp "${ENV_FILE}" "${REMOTE_ENV_FILE}"
chmod 600 "${REMOTE_ENV_FILE}"

for project in ${HOSTINGER_STOP_PROJECTS}; do
  "${DOCKER_BIN}" compose -p "${project}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" down --remove-orphans >/dev/null 2>&1 || true
 done

if [[ "${RUN_DB_SCHEMA_MIGRATION}" == "1" ]]; then
  echo "Running schema migration before container restart."
  (
    cd "${DEPLOY_DIR}"
    set -a
    # shellcheck source=/dev/null
    . "${REMOTE_ENV_FILE}"
    set +a
    bash ./infra/hostinger/migrate_supabase_schema_to_transmuter.sh
  )
else
  echo "Skipping schema migration. Set RUN_DB_SCHEMA_MIGRATION=1 to enable it."
fi

(
  cd "${DEPLOY_DIR}"
  set -a
  # shellcheck source=/dev/null
  . "${REMOTE_ENV_FILE}"
  set +a
  "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" build
  "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" up -d --remove-orphans
  "${DOCKER_BIN}" compose -p "${COMPOSE_PROJECT}" -f "${REMOTE_COMPOSE_FILE}" --env-file "${REMOTE_ENV_FILE}" ps
)

echo "Deployment command completed locally."
echo "Validate locally:"
LOCAL_WEB_BIND="${TRANSMUTER_WEB_BIND:-127.0.0.1:4301}"
LOCAL_WEB_BASE_URL="http://${LOCAL_WEB_BIND}"
echo "  curl -fsS ${LOCAL_WEB_BASE_URL}/health"
echo "  curl -fsS ${LOCAL_WEB_BASE_URL}/api/health"
